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
    parsed = [
        InformeRendimentosBase(**env) for env in _load("informe_prev_pgbl_vgbl_mesmo_cpf.json")
    ]
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


# ─────────────────────── A17 L3/L4 — financeiro_pf (Wise) + proventos ────────


def test_proventos_xp_multi_ticker_golden() -> None:
    """XP Proventos: multi-ticker, JCP 15% definitivo, bonificação ≠ renda (A17 L4)."""
    from pipeline.llm.schemas.informe_proventos import total_proventos_por_ticker

    base = InformeRendimentosBase(**_load("informe_proventos_xp_multi.json"))
    assert base.tipo_informe == "proventos_acoes"
    payload = base.proventos
    assert payload is not None
    totais = total_proventos_por_ticker(payload)
    # Bonificação ITSA4 (250.00) excluída — ITSA4 não aparece em renda.
    assert "ITSA4" not in totais
    assert totais["WEGE3"] == Decimal("492.40")
    assert totais["MXRF11"] == Decimal("96.00")
    # cnpj_pagador (XP) ≠ cnpj_fonte (WEGE3 emissora) preservados.
    wege = [p for p in payload.proventos if p.ticker == "WEGE3"][0]
    assert wege.cnpj_pagador != wege.cnpj_fonte


def test_proventos_itausa_holding_golden() -> None:
    """Itaúsa emite o informe do próprio ativo — cnpj_fonte == cnpj_emissor (A17 L4)."""
    base = InformeRendimentosBase(**_load("informe_proventos_itausa_unico.json"))
    payload = base.proventos
    assert payload is not None
    assert {p.ticker for p in payload.proventos} == {"ITSA4"}
    assert all(p.cnpj_fonte == payload.cnpj_emissor for p in payload.proventos)
    jcp = [p for p in payload.proventos if p.tipo.value == "jcp"][0]
    assert jcp.ir_retido_brl == Decimal("21.00")


def test_proventos_golden_alimenta_fiscal_source() -> None:
    """Cadeia golden → FiscalSource.proventos_summaries (yield-on-cost ITSA4)."""
    from pipeline.domain.services.fiscal_source import FiscalSource

    informe = _load("informe_proventos_xp_multi.json")
    summaries = FiscalSource.from_informes([informe]).proventos_summaries()
    itsa = [s for s in summaries if s.ticker == "ITSA4"][0]
    # 420 × 8.90 = 3738.00 de custo; bonificação não vira renda → total 0.
    assert itsa.custo_total_brl == Decimal("3738.00")
    assert itsa.total_proventos_brl == Decimal("0")


# ─────────────────── A33.l4 — goldens fim-a-fim informe → S3 ─────────────────


def _fiscal_source_proventos(*fixture_names: str):
    from pipeline.domain.services.fiscal_source import FiscalSource

    return FiscalSource.from_informes([_load(n) for n in fixture_names])


def test_proventos_golden_jcp_numerador_liquido() -> None:
    """Edge JCP: yield usa líquido (valor − IR 15% definitivo), nunca bruto."""
    summaries = _fiscal_source_proventos("informe_proventos_xp_multi.json").proventos_summaries()
    wege = [s for s in summaries if s.ticker == "WEGE3"][0]
    # dividendo 312.40 + JCP (180 − 27) = 465.40 líquido; bruto seria 492.40.
    assert wege.total_proventos_brl == Decimal("492.40")
    assert wege.renda_liquida_brl == Decimal("465.40")
    # Sem posição de custódia p/ WEGE3 → renda absoluta SEM yield (piso seguro).
    assert wege.yield_on_cost_pct is None
    assert wege.yield_on_market_pct is None


def test_proventos_golden_fii_isento() -> None:
    """Edge FII: rendimento isento PF — líquida == bruto."""
    summaries = _fiscal_source_proventos("informe_proventos_xp_multi.json").proventos_summaries()
    mxrf = [s for s in summaries if s.ticker == "MXRF11"][0]
    assert mxrf.renda_liquida_brl == Decimal("96.00")
    assert mxrf.ir_retido_brl == Decimal("0")


def test_proventos_golden_cross_payload_holding_e_corretora() -> None:
    """ITSA4 via Itaúsa (eventos) + XP (custódia) → 1 linha com os dois yields."""
    summaries = _fiscal_source_proventos(
        "informe_proventos_xp_multi.json", "informe_proventos_itausa_unico.json"
    ).proventos_summaries()
    itsa = [s for s in summaries if s.ticker == "ITSA4"]
    assert len(itsa) == 1
    s = itsa[0]
    # Itaúsa: dividendo 88.20 + JCP (140 − 21) = 207.20 líquido.
    assert s.renda_liquida_brl == Decimal("207.20")
    # XP custódia: 420 × 8.90 = 3738.00; mercado 31/12 = 4351.20.
    assert s.custo_total_brl == Decimal("3738.00")
    assert s.valor_mercado_brl == Decimal("4351.20")
    assert s.yield_on_cost_pct == Decimal("5.54")  # 207.20/3738 × 100
    assert s.yield_on_market_pct == Decimal("4.76")  # 207.20/4351.20 × 100


def test_proventos_golden_mesmo_ticker_dois_pagadores() -> None:
    """WEGE3 via XP e via BTG soma numa linha só (chave = ticker, nunca pagador)."""
    summaries = _fiscal_source_proventos(
        "informe_proventos_xp_multi.json", "informe_proventos_btg_wege.json"
    ).proventos_summaries()
    wege = [s for s in summaries if s.ticker == "WEGE3"]
    assert len(wege) == 1
    assert wege[0].renda_liquida_brl == Decimal("565.40")  # 465.40 XP + 100.00 BTG


def _store_com_informes(*fixture_names: str):
    from pipeline.artifact_store import InMemoryArtifactStore

    store = InMemoryArtifactStore()
    for name in fixture_names:
        store = store.seed("extract_informes_anuais", name.removesuffix(".json"), _load(name))
    return store


def test_proventos_golden_ate_o_payload_e5() -> None:
    """Fim-a-fim: informes no store → E5 output ``proventos_por_ativo`` (S3)."""
    from pipeline.domain.services.e5_analyzer_adapter import _try_load_proventos_summaries
    from pipeline.domain.services.e5_serialization import _proventos_summary_to_dict

    store = _store_com_informes(
        "informe_proventos_xp_multi.json", "informe_proventos_itausa_unico.json"
    )
    summaries = _try_load_proventos_summaries(store)
    rows = {r["ticker"]: r for r in (_proventos_summary_to_dict(s) for s in summaries)}
    assert rows["ITSA4"]["renda_liquida_brl"] == 207.20
    assert rows["ITSA4"]["yield_on_cost_pct"] == 5.54
    assert rows["ITSA4"]["yield_on_market_pct"] == 4.76
    assert rows["WEGE3"]["renda_liquida_brl"] == 465.40
    assert rows["WEGE3"]["yield_on_cost_pct"] is None


def test_proventos_golden_renda_por_ano_para_buckets() -> None:
    """Complemento D4: dividendos (div + FII) e JCP líquidos por ano-base."""
    fs = _fiscal_source_proventos(
        "informe_proventos_xp_multi.json",
        "informe_proventos_itausa_unico.json",
        "informe_proventos_btg_wege.json",
    )
    (renda,) = fs.proventos_renda_por_ano()
    assert renda.ano_base == 2024
    # 312.40 (WEGE3 XP) + 96.00 (MXRF11) + 88.20 (ITSA4) + 100.00 (WEGE3 BTG).
    assert renda.dividendos_liquido_brl == Decimal("596.60")
    assert renda.jcp_liquido_brl == Decimal("272.00")  # 153.00 XP + 119.00 Itaúsa


def test_informe_pf_wise_multimoeda_golden() -> None:
    """Wise: código 62 conta exterior USD/EUR; juros ME em tributáveis cód 13 (A17 L3)."""
    base = InformeRendimentosBase(**_load("informe_pf_wise_multimoeda.json"))
    assert base.tipo_informe == "financeiro_pf"
    payload = base.financeiro_pf
    assert payload is not None
    moedas = {s.moeda for s in payload.saldos_31_12}
    assert moedas == {"USD", "EUR"}
    assert all(s.codigo_rfb == "62" for s in payload.saldos_31_12)
    assert all(s.tipo.value == "conta_exterior" for s in payload.saldos_31_12)
    # Juros em ME não caem em isentos (variação cambial é GCAP, juros é carnê-leão).
    assert payload.rendimentos_isentos == []
    assert payload.rendimentos_tributaveis[0].codigo_rfb == "13"
