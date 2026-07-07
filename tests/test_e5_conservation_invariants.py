"""Invariantes de conservação por balde sobre goldens E5 (A23.l2 · guard-rail G-b) — a "segunda testemunha" que quebra sozinha se um rebaseline cimentar valor errado. Cents int (ADR-090), tolerância zero (identidade algébrica no mesmo payload, não paridade). Identidades validadas no O3: bruto == Σ composicao[].valor (por balde); liquido == bruto − dividas; fluxo_liquido == receita_total − despesa_total."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

from tests.pipeline_golden_substrate import load_fixture, run_e3_e4_e5, write_e5_config

_REPO = Path(__file__).resolve().parents[1]
_FIX = _REPO / "tests" / "fixtures" / "pipeline_golden"
_E3_MIN = _FIX / "e3" / "minimal-conta-3_reconciled.json"
_E3_MIXED = _FIX / "e3" / "minimal-conta-com-despesa-3_reconciled.json"
_BASELINE = _FIX / "e2" / "minimal-baseline-1.5_consolidated.json"
_BASELINE_DIV = _FIX / "e2" / "minimal-baseline-divergent-1.5_consolidated.json"


def _cents(value) -> int:
    return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _e3_key(path: Path) -> str:
    return path.stem.replace("-3_reconciled", "")


_CASES = {
    "minimal": (_E3_MIN, None, None),
    "mixed": (_E3_MIXED, None, {"lazer": ["CINEMA"]}),
    "baseline": (_E3_MIN, _BASELINE, None),
    "divergent": (_E3_MIN, _BASELINE_DIV, None),
}


@pytest.fixture(params=sorted(_CASES), ids=sorted(_CASES))
def e5_payload(request, tmp_path: Path) -> dict:
    e3_path, baseline_path, expense_kw = _CASES[request.param]
    write_e5_config(tmp_path, expense_keywords=expense_kw)
    return run_e3_e4_e5(
        tmp_path,
        e3_payloads={_e3_key(e3_path): load_fixture(e3_path)},
        baseline=load_fixture(baseline_path) if baseline_path else None,
    )


def test_patrimonio_bruto_equals_sum_of_buckets(e5_payload: dict):
    """bruto == Σ composicao[].valor (decomposição patrimonial por balde)."""
    pat = e5_payload["patrimonio"]
    soma = sum(_cents(b.get("valor", 0)) for b in pat.get("composicao", []))
    assert _cents(pat["bruto"]) == soma


def test_patrimonio_liquido_equals_bruto_minus_dividas(e5_payload: dict):
    pat = e5_payload["patrimonio"]
    assert _cents(pat["liquido"]) == _cents(pat["bruto"]) - _cents(pat.get("dividas", 0))


def test_fluxo_liquido_equals_receita_minus_despesa(e5_payload: dict):
    fc = e5_payload["fluxo_caixa"]
    assert _cents(fc["fluxo_liquido"]) == _cents(fc["receita_total"]) - _cents(fc["despesa_total"])


# F2-DB7 (A24.l1): decomposição POR CATEGORIA — Goodhart-safe. Mover tx entre
# categorias mantém o total e passa nos testes acima; estes quebram. Identidade
# sobre o payload serializado (round(v,2) por valor — analyze_finances.py:1444-1453);
# vale exato em cents porque dados bancários são 2dp (categorize_transactions round(Σ,2)).


def test_despesa_total_equals_sum_per_category(e5_payload: dict):
    fc = e5_payload["fluxo_caixa"]
    soma = sum(_cents(v) for v in fc.get("despesas_por_categoria", {}).values())
    assert _cents(fc["despesa_total"]) == soma


def test_receita_total_equals_sum_por_fonte(e5_payload: dict):
    fc = e5_payload["fluxo_caixa"]
    soma = sum(_cents(v) for v in fc.get("por_fonte", {}).values())
    assert _cents(fc["receita_total"]) == soma


def test_receita_total_equals_recorrente_plus_one_time(e5_payload: dict):
    fc = e5_payload["fluxo_caixa"]
    split = _cents(fc["receita_recorrente"]) + _cents(fc["receita_one_time"])
    assert _cents(fc["receita_total"]) == split
