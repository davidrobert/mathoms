"""ADR-363 — `/health` declara a revisão do executor sem sobrecarregar `version`."""

from __future__ import annotations

import fakeredis
import fakeredis.aioredis
import pytest
from pydantic import ValidationError

from backend.app.core import config as core_config
from backend.app.schemas.health import HealthResponse

_BASE = {
    "api": "ok",
    "version": "1.0.0",
    "redis": "ok",
    "celery": "ok",
    "database": "ok",
    "artifact_store_mode": "db",
    "status": "ok",
}


def test_executor_revision_e_opcional_e_nao_derruba_o_healthcheck() -> None:
    """O healthcheck de prod é `curl -fsS`: 500 aqui marcaria o container unhealthy."""
    assert HealthResponse(**_BASE).executor_revision is None
    assert HealthResponse(**_BASE, executor_revision=None).executor_revision is None
    assert HealthResponse(**_BASE, executor_revision="aaaaaaaaaaaa").executor_revision == (
        "aaaaaaaaaaaa"
    )


def test_version_continua_required_non_nullable() -> None:
    """É por isso que a revisão é campo NOVO, não o valor de `version` trocado."""
    # Mutação que mata: tornar `version` opcional "para reusar o campo" — passaria
    # a devolver null quando a env faltasse, e o `curl -fsS` derrubaria o container.
    with pytest.raises(ValidationError):
        HealthResponse(**{**_BASE, "version": None})


@pytest.mark.asyncio
async def test_endpoint_serve_api_version_e_nao_literal_stale(monkeypatch) -> None:
    """`/health` servia `"0.6.0"` hardcoded enquanto a app declarava `API_VERSION`."""
    from backend.app.main import health

    monkeypatch.setattr(core_config.settings, "BUILD_SHA", "aaaaaaaaaaaa", raising=False)
    payload = await health()

    assert payload["version"] == core_config.settings.API_VERSION
    assert payload["version"] != "0.6.0"
    assert payload["executor_revision"] == "aaaaaaaaaaaa"


@pytest.mark.asyncio
async def test_endpoint_sem_env_reporta_none_e_responde(monkeypatch) -> None:
    from backend.app.main import health

    monkeypatch.setattr(core_config.settings, "BUILD_SHA", "", raising=False)
    payload = await health()

    assert payload["executor_revision"] is None
    assert payload["api"] == "ok"


# ─── Agregado `status` × campos informacionais ───────────────────────
#
# O agregado é `all(v == "ok" ...)` sobre os checks fora de `informational`.
# `executor_revision` entrou em `checks` sem entrar no set e devolvia
# "degraded" em TODA chamada — sha de 12 chars nunca é a string "ok". Estes
# testes existem para que o PRÓXIMO campo descritivo adicionado ao payload
# quebre aqui em vez de fail-open no único sinal sumarizante do endpoint.


class _FakeCeleryInspect:
    def active(self) -> dict:
        return {"celery@fake": []}


class _FakeCeleryControl:
    def inspect(self, timeout: float | None = None) -> _FakeCeleryInspect:
        return _FakeCeleryInspect()


class _FakeCeleryApp:
    control = _FakeCeleryControl()


class _FakeConnection:
    async def __aenter__(self) -> _FakeConnection:
        return self

    async def __aexit__(self, *exc_info: object) -> bool:
        return False

    async def execute(self, statement: object) -> None:
        return None


class _FakeEngine:
    def connect(self) -> _FakeConnection:
        return _FakeConnection()


@pytest.fixture
def dependencias_sadias(monkeypatch):
    """Redis, Celery e DB respondendo — o cenário em que `status` deve ser "ok"."""
    import redis.asyncio as aioredis

    import backend.app.core.database as database_module
    import backend.app.worker as worker_module

    server = fakeredis.FakeServer()
    monkeypatch.setattr(
        aioredis,
        "from_url",
        lambda *a, **k: fakeredis.aioredis.FakeRedis(server=server, decode_responses=True),
    )
    monkeypatch.setattr(worker_module, "celery_app", _FakeCeleryApp())
    monkeypatch.setattr(database_module, "engine", _FakeEngine())
    # Setada, dispararia probe HTTP real de 2s; ambos os campos são informacionais.
    monkeypatch.delenv("MATHOMS_PIPELINE_SERVICE_URL", raising=False)


# Mutação que mata: remover `"executor_revision"` de `informational` — o estado
# entre a implementação da ADR-363 e 2026-08-08.
@pytest.mark.asyncio
async def test_status_ok_com_dependencias_sadias_e_revisao_declarada(
    dependencias_sadias, monkeypatch
) -> None:
    """Com tudo sadio o agregado é "ok" — mesmo com a revisão presente no payload."""
    from backend.app.main import health

    monkeypatch.setattr(core_config.settings, "BUILD_SHA", "aaaaaaaaaaaa", raising=False)
    payload = await health()

    # Sem este assert o teste passaria se alguém apagasse o campo do payload.
    assert payload["executor_revision"] == "aaaaaaaaaaaa"
    assert payload["status"] == "ok", payload


@pytest.mark.asyncio
async def test_status_ok_quando_a_revisao_e_desconhecida(dependencias_sadias, monkeypatch) -> None:
    """`None` também não é "ok" — subir sem `MATHOMS_BUILD_SHA` não é degradação."""
    from backend.app.main import health

    monkeypatch.setattr(core_config.settings, "BUILD_SHA", "", raising=False)
    payload = await health()

    assert payload["executor_revision"] is None
    assert payload["status"] == "ok", payload


@pytest.mark.asyncio
async def test_status_degradado_quando_dependencia_real_falha(
    dependencias_sadias, monkeypatch
) -> None:
    """Controle negativo: sem ele, `overall = "ok"` fixo passaria nos dois acima."""
    import backend.app.worker as worker_module
    from backend.app.main import health

    class _CeleryMorto:
        control = None  # `.inspect` estoura AttributeError → check vira "error: ..."

    monkeypatch.setattr(core_config.settings, "BUILD_SHA", "aaaaaaaaaaaa", raising=False)
    monkeypatch.setattr(worker_module, "celery_app", _CeleryMorto())
    payload = await health()

    assert payload["celery"].startswith("error:")
    assert payload["status"] == "degraded", payload
