"""X8 — leitor do orçamento do exec context ([[A40.l124]]): ausência nunca sai verde."""

from __future__ import annotations

import dataclasses
import io
from contextlib import redirect_stdout
from types import SimpleNamespace

import pytest

from backend.app.services.parecer_distiller import distill_exec_context_with_budget
from backend.app.services.parecer_manifest import load_manifest
from dev._unified_xchecks.orcamento import FOLGA_MINIMA, avaliar_orcamento
from pipeline.stages.parecer_planejador import _exec_context_detail
from tests.test_parecer_distiller_exec_context import make_dogfood_like_e5


def _saida(summary) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        avaliar_orcamento(summary)
    return buf.getvalue()


# O status como o STAGE o escreve — chave e campos do produtor real. Um dict montado à
# mão aqui deixaria o leitor verde sobre uma chave que o produtor não escreve.
def _status_do_stage(cap: int) -> dict:
    manifest = dataclasses.replace(load_manifest(), max_exec_context_bytes=cap)
    _texto, orcamento = distill_exec_context_with_budget(manifest, make_dogfood_like_e5())
    resultado = SimpleNamespace(exec_context=orcamento.as_dict())
    return {"success": True, **_exec_context_detail(resultado)}


def test_corpo_inteiro_com_folga_sai_verde():
    saida = _saida(_status_do_stage(load_manifest().max_exec_context_bytes))
    assert "**X8: FECHA ✅" in saida
    assert "**X8-folga: FECHA ✅" in saida


def test_eviction_diverge_contando_as_secoes_fora_do_corpo():
    status = _status_do_stage(3500)
    evictadas = len(status["exec_context"]["evicted_section_ids"])
    assert evictadas, "o cap de 3500 B tem de evictar — senão o teste é vácuo"
    saida = _saida(status)
    assert f"**X8: DIVERGE ⚠️ {evictadas}" in saida
    assert "**X8-folga: DIVERGE ⚠️ 1" in saida


def test_folga_abaixo_da_minima_diverge_mesmo_sem_eviction():
    demanda = _status_do_stage(65536)["exec_context"]["demand_bytes"]
    cap = int(demanda / (1 - FOLGA_MINIMA / 2))
    saida = _saida(_status_do_stage(cap))
    assert "**X8: FECHA ✅" in saida, "nada evictado — só a folga reprova"
    assert "**X8-folga: DIVERGE ⚠️ 1" in saida


def test_corte_degenerado_conta_como_secao_nao_vista():
    status = _status_do_stage(300)
    assert status["exec_context"]["hard_cut"]
    n_secoes = len(status["exec_context"]["section_bytes"])
    assert f"**X8: DIVERGE ⚠️ {n_secoes}" in _saida(status)


@pytest.mark.parametrize(
    "summary",
    [
        pytest.param(None, id="sem-log-do-stage"),
        pytest.param({"skipped": True, "reason": "x"}, id="stage-pulado"),
        pytest.param({"success": True}, id="anterior-a-telemetria"),
        pytest.param({"success": True, "exec_context": None}, id="orcamento-desconhecido"),
    ],
)
def test_ausencia_de_medicao_nunca_sai_verde(summary):
    saida = _saida(summary)
    assert "INAPLICAVEL" in saida
    assert "FECHA" not in saida
