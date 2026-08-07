"""Multi-worker concurrency integration test — A6f.6 (ADR-111).

Valida empiricamente o que o `docs/reference/STATELESS_AUDIT.md` afirma no papel:
a stack backend sobrevive a N uvicorn workers + M Celery workers
compartilhando o mesmo Redis + Postgres, sem nenhuma refatoração adicional.

Estratégia de simulação
-----------------------
Não spawnamos processos OS reais (flaky, lento, difícil em CI). Em vez
disso, criamos **dois clients independentes contra o mesmo `app`** +
DB + Redis (fakeredis compartilhado). Isso exercita exatamente o que
importa para stateless-safety: cada request cria sessão DB própria,
valida JWT contra `SECRET_KEY` de módulo, e faz pub/sub via Redis.

A garantia de isolamento real entre processos é propriedade do framework
(FastAPI + Celery) — não algo que a camada da aplicação possa quebrar
se seguir as regras R19 (ver `docs/reference/STATELESS_AUDIT.md`). Runbook para
teste manual multi-processo em `docs/reference/RUNBOOK.md` (cenário fail-over).

Cenários cobertos
-----------------
1. JWT válido em worker A é aceito em worker B (SECRET_KEY compartilhada).
2. Upload via worker A aparece para queries em worker B (estado em Postgres).
3. Rate limit de invitations alterna workers — 11ª tentativa é bloqueada
   (contagem via DB, não cache local).
4. WS aberto em worker A recebe evento publicado por worker C (Celery),
   Redis pub/sub é o único canal de coordenação.
"""

from __future__ import annotations

import asyncio
import json

import fakeredis
import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.app.core.security import create_access_token
from backend.app.main import app
from backend.app.models.workspace import Workspace
from backend.app.services.invitation_service import MAX_PENDING_PER_WORKSPACE
from backend.app.services.pipeline import events as events_module
from backend.tests import factories

# ─── Fixtures — dois clients simulando dois uvicorn workers ─────────


@pytest_asyncio.fixture
async def worker_a() -> AsyncClient:
    """AsyncClient independente contra `app` — simula uvicorn worker A."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://worker-a") as c:
        yield c


@pytest_asyncio.fixture
async def worker_b() -> AsyncClient:
    """AsyncClient independente contra o MESMO `app` — worker B.

    Mesmo app + mesmo DB via `TestSession` (ver conftest). O que torna
    os clients "diferentes workers" é que cada request neles roda numa
    sessão DB fresca via `get_db` dependency — não compartilham nenhum
    estado transient.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://worker-b") as c:
        yield c


# ─── Fixture — fakeredis compartilhado entre sync e async paths ─────


@pytest.fixture
def shared_redis(monkeypatch):
    """Patch sync `redis.Redis.from_url` e async `redis.asyncio.from_url`
    para apontarem para um mesmo `FakeServer`.

    Isso simula "Celery worker publica (sync) → uvicorn worker subscreve
    (async)" usando Redis como único ponto de coordenação.
    """
    server = fakeredis.FakeServer()

    def _sync_from_url(*args, **kwargs):
        return fakeredis.FakeRedis(server=server, decode_responses=True)

    def _async_from_url(*args, **kwargs):
        return fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)

    import redis
    import redis.asyncio as aioredis

    monkeypatch.setattr(redis.Redis, "from_url", _sync_from_url)
    monkeypatch.setattr(aioredis, "from_url", _async_from_url)

    # Força reset do singleton lazy em events.py — próximo publish usa
    # o cliente patched.
    events_module.reset_redis_client()
    yield server
    events_module.reset_redis_client()


# ─── Cenário 1 — JWT cross-worker ────────────────────────────────────


@pytest.mark.asyncio
async def test_jwt_issued_by_worker_a_validates_on_worker_b(
    db, worker_a: AsyncClient, worker_b: AsyncClient
):
    """Token gerado em worker A deve ser aceito em worker B — prova que
    JWT HS256 + SECRET_KEY compartilhada é a única fonte de verdade
    para auth. Nenhum estado de sessão por worker."""
    user = await factories.make_user(db, email="cross@test.com")
    await db.commit()

    token = create_access_token(user.id, token_version=user.token_version)

    # Worker A registra o uso (headers); worker B autentica independente.
    worker_a.headers["Authorization"] = f"Bearer {token}"
    resp_a = await worker_a.get("/api/auth/me")
    assert resp_a.status_code == 200
    assert resp_a.json()["id"] == user.id

    # O MESMO token, enviado via worker B — sem qualquer coordenação
    # prévia entre workers — deve validar.
    worker_b.headers["Authorization"] = f"Bearer {token}"
    resp_b = await worker_b.get("/api/auth/me")
    assert resp_b.status_code == 200
    assert resp_b.json()["id"] == user.id
    assert resp_b.json()["email"] == "cross@test.com"


# ─── Cenário 2 — Estado persistente cross-worker ─────────────────────


@pytest.mark.asyncio
async def test_workspace_created_via_worker_a_visible_on_worker_b(
    db, worker_a: AsyncClient, worker_b: AsyncClient
):
    """Recurso criado via worker A é visível imediatamente via worker B
    porque o estado de registro está em Postgres, não em cache local."""
    owner = await factories.make_user(db, email="owner@test.com")
    token = create_access_token(owner.id, token_version=owner.token_version)
    worker_a.headers["Authorization"] = f"Bearer {token}"
    worker_b.headers["Authorization"] = f"Bearer {token}"

    # Worker A cria o workspace via commit direto no DB (simulando lado
    # efeito de um endpoint de criação; o que importa é que worker A
    # escreveu, worker B deve ler).
    ws = await factories.make_workspace(db, owner=owner, name="Cross-worker ws")
    await db.commit()

    # Worker B lista workspaces do user — sem nenhuma pista de que a
    # escrita veio de worker A. Endpoint é `/api/me/workspaces`.
    resp = await worker_b.get("/api/me/workspaces")
    assert resp.status_code == 200
    found = {w["id"]: w["name"] for w in resp.json()["workspaces"]}
    assert ws.id in found
    assert found[ws.id] == "Cross-worker ws"


# ─── Cenário 3 — Rate limit compartilhado ────────────────────────────


@pytest.mark.asyncio
async def test_invitation_rate_limit_counts_across_workers(
    db, worker_a: AsyncClient, worker_b: AsyncClient
):
    """Criar `MAX_PENDING_PER_WORKSPACE` convites alternando workers A/B.
    O (N+1)-ésimo deve receber 429 — contagem em Postgres, nunca em
    memória local de um worker."""
    owner = await factories.make_user(db, email="owner@test.com")
    ws = await factories.make_workspace(db, owner=owner)
    await db.commit()

    token = create_access_token(owner.id, token_version=owner.token_version)
    worker_a.headers["Authorization"] = f"Bearer {token}"
    worker_b.headers["Authorization"] = f"Bearer {token}"

    clients = [worker_a, worker_b]
    for i in range(MAX_PENDING_PER_WORKSPACE):
        c = clients[i % 2]  # alternância estrita A/B
        resp = await c.post(
            f"/api/workspaces/{ws.id}/invitations",
            json={"email": f"inv{i}@test.com", "role": "viewer"},
        )
        assert (
            resp.status_code == 201
        ), f"convite #{i} via {c.base_url} falhou: {resp.status_code} {resp.text}"

    # (N+1)-ésimo convite — não importa qual worker envie, deve 429.
    over = await worker_b.post(
        f"/api/workspaces/{ws.id}/invitations",
        json={"email": "over@test.com", "role": "viewer"},
    )
    assert over.status_code == 429
    assert over.json()["detail"]["code"] == "limit_reached"


# ─── Cenário 4 — WS recebe evento publicado por outro worker ────────


def test_ws_on_worker_a_receives_event_from_celery_worker(shared_redis):
    """WebSocket aceito em worker A recebe evento publicado via `publish_event`
    (simulando worker Celery). Ambos falam com o MESMO `fakeredis.FakeServer` —
    se o teste passa, confirma que a única ponte entre workers é o Redis.

    Usa `TestClient` sync porque starlette exige sync client para
    `.websocket_connect()`.
    """
    from fastapi.testclient import TestClient

    user_id = "user-xyz"
    run_id = "run-cross-worker-42"
    token = create_access_token(user_id)

    client = TestClient(app)
    with client.websocket_connect(f"/api/pipeline/runs/{run_id}/ws?token={token}") as ws:
        # "Celery worker" publica via events.publish_event — usa
        # redis.Redis.from_url (sync) que foi patchado para FakeRedis.
        events_module.publish_stage_started(run_id, "E3", 30)

        # O WS subscriber (no worker uvicorn) recebe via pub/sub.
        # Pode chegar heartbeat primeiro (timeout interno de 15s) —
        # loop limitado a 3 leituras para filtrar.
        received = None
        for _ in range(3):
            msg = ws.receive_json()
            if msg.get("event") == "stage_started":
                received = msg
                break
        assert received is not None, "stage_started não chegou via pub/sub"
        assert received["run_id"] == run_id
        assert received["stage"] == "E3"


def test_ws_terminal_event_closes_connection_cross_worker(shared_redis):
    """Terminal event (`run_completed`) publicado por Celery fecha o WS
    aberto no worker uvicorn — confirma que o fluxo de encerramento
    também viaja 100% via Redis."""
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect

    user_id = "user-term"
    run_id = "run-term-7"
    token = create_access_token(user_id)

    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/api/pipeline/runs/{run_id}/ws?token={token}") as ws:
            events_module.publish_run_completed(run_id, status="completed")
            # Drena até receber run_completed (ou WebSocketDisconnect).
            for _ in range(5):
                msg = ws.receive_json()
                if msg.get("event") == "run_completed":
                    # servidor fecha logo em seguida com code=1000
                    ws.receive_json()  # deve levantar WebSocketDisconnect
                    break


# ─── Cenário 5 — Decision.code gerado server-side sem colisão (ADR-214) ──


@pytest.mark.asyncio
async def test_concurrent_decision_creation_no_code_collision(db, client):
    """ADR-214 — N requests HTTP encadeados criando Decision no mesmo
    workspace produzem N codes únicos sequenciais.

    Cada POST entra com sua própria ``AsyncSession`` (via dependency
    override ``_override_get_db``). O contrato testado: server gera
    ``D{N:02d}`` monotonicamente, sem colisão e sem gap. Em Postgres
    real (CI/staging), ``pg_advisory_xact_lock`` per-workspace cobre o
    caso adversário (workers paralelos competindo); este teste exercita
    a serialização via HTTP, que é o caminho real de produção.
    """
    from backend.tests import factories

    owner = await factories.make_user(db, email="dec-concurrency@test.com")
    ws = await factories.make_workspace(db, owner=owner)
    await db.commit()

    from backend.app.core.security import create_access_token

    token = create_access_token(owner.id, token_version=owner.token_version)
    client.headers["Authorization"] = f"Bearer {token}"

    n = 10
    base = f"/api/workspaces/{ws.id}/decisions"
    codes: list[str] = []
    for i in range(n):
        resp = await client.post(base, json={"title": f"Decisão {i}"})
        assert resp.status_code == 201, f"#{i}: {resp.status_code} {resp.text}"
        codes.append(resp.json()["code"])

    assert len(set(codes)) == n, f"codes duplicados: {codes}"
    nums = sorted(int(c[1:]) for c in codes)
    assert nums == list(range(1, n + 1)), f"sequência inesperada: {nums}"
