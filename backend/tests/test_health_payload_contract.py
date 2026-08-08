"""Contrato do payload de `/health` — o que o endpoint emite atravessa o `response_model`.

Os testes da ADR-363 chamam `health()` direto e leem chaves do dict devolvido:
nenhum atravessa `response_model=HealthResponse`, que é onde o FastAPI valida a
resposta de verdade. Um check que passasse a devolver algo fora do tipo
declarado — ou `status` fora do `Literal["ok", "degraded"]` — só quebraria em
produção. Aqui o payload vai pelo HTTP, como o cliente o recebe.
"""

from __future__ import annotations

import pytest

import backend.app.main as main_module
import backend.app.worker as worker_module
from backend.app.core import config as core_config
from backend.app.schemas.health import HealthResponse
from backend.tests.fakes import DeadCeleryApp, patch_healthy_dependencies


async def _probe_sempre_alcancavel(url: str) -> bool:
    return True


def _config_sadia(mp) -> None:
    patch_healthy_dependencies(mp)


def _config_cache_separado(mp) -> None:
    """Cache Redis em host próprio (broker noeviction × cache LRU) — emite `redis_cache`."""
    patch_healthy_dependencies(mp)
    mp.setattr(core_config.settings, "REDIS_CACHE_URL", "redis://cache-host:6379/1", raising=False)


def _config_pipeline_service(mp) -> None:
    """Cutover HTTP (ADR-112) — `pipeline_service_reachable` vira bool, não `None`."""
    patch_healthy_dependencies(mp)
    mp.setenv("MATHOMS_PIPELINE_SERVICE_URL", "http://pipeline-service:8001")
    mp.setattr(main_module, "_probe_pipeline_service", _probe_sempre_alcancavel)


def _config_degradada(mp) -> None:
    patch_healthy_dependencies(mp)
    mp.setattr(worker_module, "celery_app", DeadCeleryApp())


# Cada ramo condicional de `health()` que muda o CONJUNTO de chaves ou o TIPO de
# um valor. Um ramo que não aparecer aqui fica fora dos testes de paridade abaixo.
_CONFIGURACOES = (
    _config_sadia,
    _config_cache_separado,
    _config_pipeline_service,
    _config_degradada,
)


# A fonte é o dict do endpoint, NÃO `response.json()`: o `response_model`
# materializa o default de todo campo declarado, então o payload HTTP contém
# `campo: null` mesmo quando o endpoint não emite o campo. Medir ali torna a
# direção "declarado mas nunca emitido" invisível — verificado por mutação
# (um campo morto no schema sobrevivia ao teste).
async def _keys_emitidas_pelo_endpoint(monkeypatch) -> set[str]:
    """União das chaves que `health()` põe em `checks` em cada ramo condicional."""
    from backend.app.main import health

    keys: set[str] = set()
    for configurar in _CONFIGURACOES:
        with monkeypatch.context() as mp:
            configurar(mp)
            keys |= set(await health())
    return keys


@pytest.mark.asyncio
async def test_payload_sadio_atravessa_o_response_model(client, monkeypatch) -> None:
    """200 aqui é a asserção: um valor fora do tipo declarado viraria 500 em produção."""
    patch_healthy_dependencies(monkeypatch)
    monkeypatch.setattr(core_config.settings, "BUILD_SHA", "aaaaaaaaaaaa", raising=False)

    resp = await client.get("/health")

    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ok", resp.json()
    assert resp.json()["executor_revision"] == "aaaaaaaaaaaa"


@pytest.mark.asyncio
async def test_payload_degradado_atravessa_o_response_model(client, monkeypatch) -> None:
    """A string livre de exceção em `celery` também precisa serializar."""
    patch_healthy_dependencies(monkeypatch)
    monkeypatch.setattr(worker_module, "celery_app", DeadCeleryApp())

    resp = await client.get("/health")

    assert resp.status_code == 200, resp.text
    assert resp.json()["celery"].startswith("error:")
    assert resp.json()["status"] == "degraded", resp.json()


@pytest.mark.asyncio
async def test_cutover_http_do_pipeline_service_serializa_e_nao_degrada(
    client, monkeypatch
) -> None:
    """`pipeline_service_reachable` é `Optional[bool]`; ambos os campos são informacionais."""
    with monkeypatch.context() as mp:
        _config_pipeline_service(mp)
        resp = await client.get("/health")

    assert resp.status_code == 200, resp.text
    assert resp.json()["pipeline_service_url"] == "http://pipeline-service:8001"
    assert resp.json()["pipeline_service_reachable"] is True
    assert resp.json()["status"] == "ok", resp.json()


@pytest.mark.asyncio
async def test_todo_ramo_condicional_atravessa_o_response_model(client, monkeypatch) -> None:
    """Inclusive os ramos que só existem em prod (cache separado, cutover HTTP)."""
    for configurar in _CONFIGURACOES:
        with monkeypatch.context() as mp:
            configurar(mp)
            resp = await client.get("/health")
            assert resp.status_code == 200, f"{configurar.__name__}: {resp.text}"


# `model_config = ConfigDict(extra="allow")` NÃO filtra campo não declarado: ele
# viaja ao cliente sem existir no OpenAPI (verificado — era o caso de `redis_cache`).
@pytest.mark.asyncio
async def test_todo_campo_emitido_esta_declarado_no_response_model(monkeypatch) -> None:
    emitidas = await _keys_emitidas_pelo_endpoint(monkeypatch)

    nao_declaradas = emitidas - set(HealthResponse.model_fields)

    assert not nao_declaradas, (
        f"campos emitidos por /health e ausentes do HealthResponse: {sorted(nao_declaradas)} — "
        "declare no schema e rode `make update-openapi-snapshot`"
    )


# Direção inversa: campo declarado que nenhum ramo emite é promessa falsa no
# OpenAPI. Se o campo é legitimamente condicional, o ramo entra em _CONFIGURACOES.
@pytest.mark.asyncio
async def test_todo_campo_declarado_e_realmente_emitido(monkeypatch) -> None:
    emitidas = await _keys_emitidas_pelo_endpoint(monkeypatch)

    nunca_emitidas = set(HealthResponse.model_fields) - emitidas

    assert (
        not nunca_emitidas
    ), f"campos declarados no HealthResponse que /health nunca emite: {sorted(nunca_emitidas)}"
