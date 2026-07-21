"""Invariantes de conservação por balde sobre goldens E5 (A23.l2 · guard-rail G-b) — a "segunda testemunha" que quebra sozinha se um rebaseline cimentar valor errado. Cents int (ADR-090), tolerância zero (identidade algébrica no mesmo payload, não paridade). Identidades validadas no O3: bruto == Σ composicao[].valor (por balde); liquido == bruto − dividas; fluxo_liquido == receita_total − despesa_total."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

from pipeline.llm.schemas.e16_irpf_full import (
    CodigoRendimentoIsento,
    CodigoRendimentoTribExclusiva,
)
from tests.pipeline_golden_substrate import load_fixture, run_e3_e4_e5, write_e5_config
from tests.unit.pipeline._passive_income_builders import (
    bem,
    decl,
    exclusiva,
    exterior_rend,
    isento,
)

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


# DE-02 (R3.4b): conservação da renda passiva observada (ADR-191 + ADR-336). O
# numerador da TRS (renda_passiva_anual) é só yield RECORRENTE — exclui a
# distribuição de lucro PJ do titular (renda de trabalho, ADR-191) e o ganho de
# capital (realização one-time, ADR-336). Exige fixture IRPF-bearing com
# distribuicao_pj_titular>0 E ganho_capital>0, senão o teste é vacuoso (0==0).
# CNPJ/empresa fictícios (ACME LTDA), PII-zero.
_QUOTA_ACME = "QUOTAS DA EMPRESA ACME SERVICOS LTDA CNPJ 12.345.678/0001-90"
_YIELD_BUCKETS = ("dividendos", "jcp", "aplicacoes", "exterior", "alugueis")


def _irpf_bearing_payload() -> dict:
    """IRPF sintético com os 6 buckets não-zero + distribuição PJ do titular."""
    return decl(
        isentos=[
            isento(CodigoRendimentoIsento.lucros_dividendos, "12000.00"),
            isento(
                CodigoRendimentoIsento.lucros_dividendos,
                "284000.00",
                fonte="12.345.678/0001-90 ACME SERVICOS LTDA",
                descricao="Lucros e dividendos recebidos",
            ),
        ],
        exclusiva_list=[
            exclusiva(CodigoRendimentoTribExclusiva.jcp, "30000.00"),
            exclusiva(CodigoRendimentoTribExclusiva.rendimentos_aplicacoes_financeiras, "3000.00"),
            exclusiva(CodigoRendimentoTribExclusiva.ganho_capital, "20000.00"),
        ],
        exterior=[exterior_rend("8000.00")],
        bens=[bem(descricao=_QUOTA_ACME, valor="500000.00")],
    ).model_dump(mode="json")


def test_renda_passiva_conservation(tmp_path: Path):
    write_e5_config(tmp_path)
    e5 = run_e3_e4_e5(
        tmp_path,
        e3_payloads={_e3_key(_E3_MIN): load_fixture(_E3_MIN)},
        baseline=load_fixture(_BASELINE),
        irpf_payloads={"irpfdeclaracao_2024": _irpf_bearing_payload()},
    )
    pi = e5["passive_income"]
    assert pi["status"] == "ok", "fixture vacuosa — passive_income precisa ser 'ok'"
    fonte = pi["renda_passiva_por_fonte_brl"]
    distribuicao = _cents(fonte["distribuicao_pj_titular"])
    ganho = _cents(fonte["ganho_capital"])
    assert distribuicao > 0 and ganho > 0, "guard anti-vacuidade (subtração seria 0)"
    yield_rec = sum(_cents(fonte[k]) for k in _YIELD_BUCKETS)
    soma = sum(_cents(v) for v in fonte.values())
    anual = _cents(pi["renda_passiva_anual_brl"])
    assert anual == yield_rec == soma - distribuicao - ganho


def test_cv17_runtime_check_passes_on_golden(tmp_path: Path):
    """CV17 (A37.l7 · CTO-01) é o gêmeo runtime de test_renda_passiva_conservation:
    sobre o mesmo payload IRPF-bearing não-vacuoso, o check de `validate_cross`
    tem que ficar verde — prova que o gate cobre o payload real, não só o golden."""
    from scripts import validate_cross

    write_e5_config(tmp_path)
    e5 = run_e3_e4_e5(
        tmp_path,
        e3_payloads={_e3_key(_E3_MIN): load_fixture(_E3_MIN)},
        baseline=load_fixture(_BASELINE),
        irpf_payloads={"irpfdeclaracao_2024": _irpf_bearing_payload()},
    )
    fonte = e5["passive_income"]["renda_passiva_por_fonte_brl"]
    assert _cents(fonte["distribuicao_pj_titular"]) > 0, "guard anti-vacuidade"
    result = validate_cross._cv17_renda_passiva_conservacao(e5)
    assert result is not None and result.passed
    assert result.severity == "info"
