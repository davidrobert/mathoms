"""O orçamento do exec context sai do orchestrator e do stage ([[ADR-341]] §Emenda 2026-10-09).

[[A40.l124]]: a eviction tirou investimentos e independência financeira do parecer do
dogfood por seis semanas e nada fora do modelo soube. Os testes leem o que FOI ENVIADO
(o `user_prompt` que o fake registra) e o que FOI PUBLICADO (resultado, log, status do
stage) — e exigem que digam a mesma coisa.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import re
from contextlib import contextmanager
from pathlib import Path

import pytest

from backend.app.services import parecer_orchestrator as orch
from backend.app.services.parecer_orchestrator import (
    ParecerOrchestratorConfig,
    generate_parecer,
    load_manifest,
)
from backend.app.services.storage.llm_cache import InMemoryLLMCache
from tests.fakes.parecer import FailingLLM, FakeLLMService
from tests.test_parecer_planejador_golden import make_canned_output, make_workspace_e5

_LOGGER = "mathoms.llm.parecer_planejador"
_EVENTO = "parecer_planejador_exec_context"
_MARKER_IDS = re.compile(r"seções removidas por prioridade: ([a-z0-9_, ]+)\.")
# 5 seções saem do e5 do golden neste cap, sem corte degenerado (medido).
_CAP_COM_EVICTION = 5000


@pytest.fixture
def cap_apertado(monkeypatch):
    manifest = dataclasses.replace(load_manifest(), max_exec_context_bytes=_CAP_COM_EVICTION)
    monkeypatch.setattr(orch, "load_manifest", lambda *a, **k: manifest)
    return manifest


# Handler no PRÓPRIO logger e `disabled` forçado: outro módulo da suíte reconfigura o
# logging e desliga loggers existentes — `caplog` no root sairia vazio só na suíte.
@contextmanager
def _eventos():
    logger, registros = logging.getLogger(_LOGGER), []

    class _Coletor(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            if record.getMessage() == _EVENTO:
                registros.append(record)

    handler, anterior = _Coletor(level=logging.DEBUG), (logger.level, logger.disabled)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.disabled = False
    try:
        yield registros
    finally:
        logger.removeHandler(handler)
        logger.setLevel(anterior[0])
        logger.disabled = anterior[1]


def _gerar(llm, cache=None, ws: str = "ws-exec-context"):
    return generate_parecer(
        e5_data=make_workspace_e5(),
        config=ParecerOrchestratorConfig(workspace_id=ws, tier="premium"),
        llm_service=llm,
        cache=cache if cache is not None else InMemoryLLMCache(),
    )


def _ids_enviados(user_prompt: str) -> list[str]:
    achado = _MARKER_IDS.search(user_prompt)
    return [i.strip() for i in achado.group(1).split(",")] if achado else []


def test_resultado_diz_o_que_o_marcador_disse_ao_modelo(cap_apertado):
    llm = FakeLLMService(output=make_canned_output())
    result = _gerar(llm)
    enviados = _ids_enviados(llm.last_call_kwargs["user_prompt"])
    assert enviados, "o cap apertado tem de evictar — senão o teste é vácuo"
    assert result.exec_context["evicted_section_ids"] == enviados
    assert result.exec_context["cap_bytes"] == _CAP_COM_EVICTION


def test_evento_sai_mesmo_quando_a_chamada_falha_e_em_warning(cap_apertado):
    """A chamada falha e o log ainda diz o que o modelo ia receber."""
    with _eventos() as registros:
        result = _gerar(FailingLLM())
    assert result.status == "needs_review"
    assert result.exec_context and result.exec_context["evicted_section_ids"]
    assert [r.levelno for r in registros] == [logging.WARNING]
    assert registros[0].evicted_section_ids == result.exec_context["evicted_section_ids"]


def test_sem_eviction_o_evento_e_info():
    with _eventos() as registros:
        result = _gerar(FakeLLMService(output=make_canned_output()))
    assert result.exec_context["evicted_section_ids"] == []
    assert [r.levelno for r in registros] == [logging.INFO]


def test_evento_carrega_so_inteiros_e_ids_de_secao(cap_apertado):
    with _eventos() as registros:
        _gerar(FakeLLMService(output=make_canned_output()))
    ids = {s["id"] for s in cap_apertado.sections}
    rec = registros[0]
    assert set(rec.section_bytes) == ids and all(
        isinstance(v, int) for v in rec.section_bytes.values()
    )
    assert set(rec.evicted_section_ids) <= ids
    for campo in ("cap_bytes", "demand_bytes", "body_bytes", "hints_bytes", "catalog_bytes"):
        assert isinstance(getattr(rec, campo), int)


def test_cache_hit_devolve_o_orcamento_guardado_sem_reemitir(cap_apertado):
    cache = InMemoryLLMCache()
    primeiro = _gerar(FakeLLMService(output=make_canned_output()), cache=cache)
    with _eventos() as registros:
        hit = _gerar(FakeLLMService(output=make_canned_output()), cache=cache)
    assert hit.cache_hit and hit.exec_context == primeiro.exec_context
    assert registros == [], "hit não monta prompt — re-emitir mentiria sobre uma chamada"


def test_envelope_anterior_a_telemetria_le_desconhecido_e_nao_vazio():
    cache = InMemoryLLMCache()
    _gerar(FakeLLMService(output=make_canned_output()), cache=cache)
    for key, (raw, expira) in list(cache._store.items()):
        envelope = json.loads(raw)
        envelope.pop("exec_context")
        cache._store[key] = (json.dumps(envelope), expira)
    hit = _gerar(FakeLLMService(output=make_canned_output()), cache=cache)
    assert hit.cache_hit and hit.exec_context is None


# --------------------------------------------------------------------------------------
# Stage: o status vira `pipeline_stage_logs.output_summary` nos DOIS desfechos
# --------------------------------------------------------------------------------------


def _ctx_do_stage(tmp_path: Path):
    from pipeline.artifact_store import InMemoryArtifactStore
    from pipeline.context import WorkspaceContext

    store = InMemoryArtifactStore()
    store.seed("E5", "analise_financeira", make_workspace_e5())
    return WorkspaceContext(
        root=tmp_path,
        artifact_store=store,
        workspace_id="ws-stage-exec-context",
        config_overrides={"llm_config.json": {"api_key": "sk-mock"}},
    )


@pytest.fixture
def rodar_stage(monkeypatch, tmp_path):
    from pipeline.stages import parecer_planejador as stage_mod

    original = orch.generate_parecer

    def _rodar(llm):
        def com_fakes(**kwargs):
            return original(**kwargs, llm_service=llm, cache=InMemoryLLMCache())

        monkeypatch.setattr(orch, "generate_parecer", com_fakes)
        return stage_mod.run(_ctx_do_stage(tmp_path))

    return _rodar


def test_status_do_stage_publica_o_orcamento_no_sucesso(rodar_stage):
    status = rodar_stage(FakeLLMService(output=make_canned_output()))
    assert status["success"] is True
    assert status["exec_context"]["cap_bytes"] == load_manifest().max_exec_context_bytes
    assert status["exec_context"]["evicted_section_ids"] == []


def test_status_do_stage_publica_o_orcamento_no_needs_review(rodar_stage):
    status = rodar_stage(FailingLLM())
    assert status["status"] == "needs_review"
    assert status["exec_context"]["demand_bytes"] > 0
