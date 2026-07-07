"""Goldens A33.l2 (ADR-238 §D1 · KR4) — Wise 3 cenários needs_review + banco BRL limpo.

Co-design financial-planner 2026-07-07: validações Wise vivem na camada
pós-extração (merger/E5), nunca em model_validator do boundary — o golden
`informe_pf_wise_flags_p5.json` passa Pydantic (extração legítima) e os
flags nascem nos detectors. `informe_pf_banco_brl_limpo.json` prova o
inverso: banco BRL puro atravessa merger com zero warnings e zero flags.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from pipeline.domain.services.baseline_informe_merger import BaselineInformeMerger
from pipeline.domain.services.ptax_types import PtaxQuote
from pipeline.llm.schemas.informe_base import InformeRendimentosBase

_GOLDEN_DIR = Path(__file__).parent / "fixtures" / "llm_golden"

_PTAX_2024 = {"USD": Decimal("6.1917"), "EUR": Decimal("6.4344"), "GBP": Decimal("7.7570")}


def _load(name: str) -> dict:
    return json.loads((_GOLDEN_DIR / name).read_text(encoding="utf-8"))


def _ptax_31_12(moeda: str, ano_base: int) -> PtaxQuote | None:
    rate = _PTAX_2024.get(moeda) if ano_base == 2024 else None
    if rate is None:
        return None
    return PtaxQuote(rate=rate, observed_at=date(ano_base, 12, 31))


def _ptax_bootstrap_only(moeda: str, ano_base: int) -> PtaxQuote | None:
    """Simula DB só com row de bootstrap (fora de dezembro) — converter degradaria p/ None."""
    return None


# ─────────────────────── validade Pydantic dos goldens ──────────────────────


def test_golden_brl_limpo_valida_no_boundary() -> None:
    base = InformeRendimentosBase(**_load("informe_pf_banco_brl_limpo.json"))
    assert base.tipo_informe == "financeiro_pf"
    assert base.financeiro_pf is not None
    assert all(s.moeda == "BRL" for s in base.financeiro_pf.saldos_31_12)


def test_golden_wise_flags_valida_no_boundary() -> None:
    """Extração com misclassificações fiscais é LEGÍTIMA no boundary (zero hard-fail P5)."""
    base = InformeRendimentosBase(**_load("informe_pf_wise_flags_p5.json"))
    payload = base.financeiro_pf
    assert payload is not None
    assert {s.moeda for s in payload.saldos_31_12} == {"USD", "EUR"}


# ─────────────────────── merger: banco BRL limpo → zero ruído ────────────────


def test_golden_brl_limpo_zero_warnings_zero_flags() -> None:
    merger = BaselineInformeMerger(ptax_getter=_ptax_31_12)
    r = merger.merge({}, [_load("informe_pf_banco_brl_limpo.json")])
    assert r.saldos_added == 2
    assert r.warnings == []
    assert r.fiscal_flags == []
    assert r.baseline["wise_fiscal_flags"] == []
    for entry in r.baseline["informe_pf_saldos_31_12"]:
        assert entry["moeda"] == "BRL"
        assert entry["saldo_brl"] == entry["saldo_original"]
        assert entry["fonte"] == "informe_31_12"


# ─────────────────────── merger: Wise 3 cenários needs_review ────────────────


def test_golden_wise_3_cenarios_needs_review() -> None:
    """41-em-ME + variação cambial em isentos + juros ME mal-alocado → 3 pontos."""
    merger = BaselineInformeMerger(ptax_getter=_ptax_31_12)
    r = merger.merge({}, [_load("informe_pf_wise_flags_p5.json")])
    needs = [f for f in r.fiscal_flags if f.needs_review]
    assert {f.code for f in needs} == {"RFB41_ME", "GCAP_ISENTO", "CARNELEAO"}
    assert len(needs) == 3
    # GCAP exposição continua como fact-check (sem needs_review).
    gcap = [f for f in r.fiscal_flags if f.code == "GCAP"]
    assert len(gcap) == 1 and gcap[0].needs_review is False


def test_golden_wise_conversao_ptax_31_12() -> None:
    """USD 5210.55 × 6,1917 = 32262,16 BRL (quantize 2 casas); ptax_data comprova 31/12."""
    merger = BaselineInformeMerger(ptax_getter=_ptax_31_12)
    r = merger.merge({}, [_load("informe_pf_wise_flags_p5.json")])
    usd = [e for e in r.baseline["informe_pf_saldos_31_12"] if e["moeda"] == "USD"][0]
    assert usd["saldo_brl"] == "32262.16"
    assert usd["taxa_ptax_aplicada"] == "6.1917"
    assert usd["ptax_data"] == "2024-12-31"
    assert usd["ptax_status"] == "applied"
    assert r.warnings == []


def test_golden_wise_multimoeda_existente_juros_bem_alocado_e_footnote() -> None:
    """Fixture shipped (P1): juros cód 13 em tributáveis → footnote info, sem needs_review."""
    merger = BaselineInformeMerger(ptax_getter=_ptax_31_12)
    r = merger.merge({}, [_load("informe_pf_wise_multimoeda.json")])
    carne = [f for f in r.fiscal_flags if f.code == "CARNELEAO"]
    assert len(carne) == 1
    assert carne[0].severity == "info"
    assert carne[0].needs_review is False
    assert not any(f.code in ("RFB41_ME", "GCAP_ISENTO") for f in r.fiscal_flags)


def test_golden_regressao_bootstrap_nao_converte() -> None:
    """REGRESSÃO (co-design DE 2026-07-07): sem PTAX de dezembro do ano-base,
    a conversão NÃO usa cotação stale — degrada para None + warning tipado."""
    merger = BaselineInformeMerger(ptax_getter=_ptax_bootstrap_only)
    r = merger.merge({}, [_load("informe_pf_wise_flags_p5.json")])
    me_entries = [e for e in r.baseline["informe_pf_saldos_31_12"] if e["moeda"] != "BRL"]
    assert me_entries and all(e["saldo_brl"] is None for e in me_entries)
    assert all(e["ptax_status"] == "missing" for e in me_entries)
    assert {w.moeda for w in r.warnings} == {"USD", "EUR"}
