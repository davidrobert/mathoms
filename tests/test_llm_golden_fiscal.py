"""Goldens fiscais BR (A20.l12 W2-T02) — previdência ×7 + e15 ×2 + e2_llm + e16.

Casos do público-alvo alta renda PJ (revisão financial-planner na lane):
PGBL/VGBL, patrocinador, regimes mistos, portabilidade, info_fiscal_anual
anti-double-count (ADR-242) e degradação graceful de declaração truncada.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from pipeline.llm.schemas.e2_llm_extract import LLMExtractOutput
from pipeline.llm.schemas.e15_baseline import BaselinePatrimonialOutput
from pipeline.llm.schemas.e16_irpf_full import IRPFFullOutput
from pipeline.llm.schemas.informe_base import InformeRendimentosBase

GOLDEN_DIR = Path(__file__).resolve().parent / "fixtures" / "llm_golden"

_PREV_SINGLE = (
    "informe_prev_pgbl_progressivo.json",
    "informe_prev_pgbl_regressivo.json",
    "informe_prev_vgbl_progressivo.json",
    "informe_prev_pgbl_patrocinador.json",
    "informe_prev_portabilidade.json",
)
_PREV_MULTI = (
    "informe_prev_pgbl_vgbl_mesmo_cpf.json",
    "informe_prev_regimes_mistos.json",
)


def _load(name: str):
    return json.loads((GOLDEN_DIR / name).read_text())


@pytest.mark.parametrize("fixture_name", _PREV_SINGLE)
def test_previdencia_golden_valida(fixture_name: str) -> None:
    base = InformeRendimentosBase(**_load(fixture_name))
    assert base.tipo_informe == "previdencia_privada"
    assert base.previdencia is not None
    assert base.previdencia.saldo_31_12 > Decimal("0")


@pytest.mark.parametrize("fixture_name", _PREV_MULTI)
def test_previdencia_golden_multi_plano(fixture_name: str) -> None:
    """ADR-238 D2: 1 plano = 1 payload — casos multi-plano são N envelopes."""
    envelopes = [_load_env for _load_env in _load(fixture_name)]
    parsed = [InformeRendimentosBase(**env) for env in envelopes]
    assert len(parsed) == 2
    certificados = {p.previdencia.numero_certificado for p in parsed}
    assert len(certificados) == 2


def test_previdencia_pgbl_vgbl_mesmo_cpf_tem_tipos_distintos() -> None:
    parsed = [InformeRendimentosBase(**env) for env in _load("informe_prev_pgbl_vgbl_mesmo_cpf.json")]
    assert {p.previdencia.plano_tipo.value for p in parsed} == {"pgbl", "vgbl"}


def test_previdencia_regimes_mistos_mesmo_tipo() -> None:
    parsed = [InformeRendimentosBase(**env) for env in _load("informe_prev_regimes_mistos.json")]
    assert {p.previdencia.plano_tipo.value for p in parsed} == {"pgbl"}
    assert {p.previdencia.regime_tributacao.value for p in parsed} == {
        "progressivo",
        "regressivo",
    }


def test_previdencia_patrocinador_needs_review() -> None:
    base = InformeRendimentosBase(**_load("informe_prev_pgbl_patrocinador.json"))
    assert base.needs_review is True
    assert base.confidence < 0.7


def test_previdencia_portabilidade_saldos_divergem() -> None:
    base = InformeRendimentosBase(**_load("informe_prev_portabilidade.json"))
    prev = base.previdencia
    assert prev.saldo_01_01 != prev.saldo_31_12_ano_anterior


@pytest.mark.parametrize(
    "fixture_name", ("e15_baseline_truncada.json", "e15_baseline_com_dependente.json")
)
def test_e15_golden_extras_validam(fixture_name: str) -> None:
    out = BaselinePatrimonialOutput(**_load(fixture_name))
    assert out.items


def test_e15_truncada_confidence_baixa() -> None:
    out = BaselinePatrimonialOutput(**_load("e15_baseline_truncada.json"))
    assert out.confidence < 0.7
    assert out.notes


def test_e2_llm_info_fiscal_anual_anti_double_count() -> None:
    """ADR-242: linha de informe IR acumulado é sinalizada e fica fora do fluxo."""
    out = LLMExtractOutput(**_load("e2_llm_info_fiscal_anual.json"))
    hints = {t.category_hint for t in out.transactions}
    assert hints == {"info_fiscal_anual"}


def test_e16_fail_gracefully_valida_com_confidence_baixa() -> None:
    out = IRPFFullOutput(**_load("e16_irpf_full_fail_gracefully.json"))
    assert out.confidence <= 0.5
    assert out.notes
