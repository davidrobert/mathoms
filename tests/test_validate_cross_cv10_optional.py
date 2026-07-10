"""Calibração CV10 (A36.l3 FU-1): completude só dos gráficos obrigatórios.

Bug: `_cv10_charts_completeness` marcava como "incompleto" qualquer gráfico com
`context`/`conclusion` vazio — inclusive opcionais legitimamente vazios
(`impostos_pj`, `wise_fiscal_flags`) quando o workspace não tem PJ/Wise, gerando
`warning` falso-positivo. Fix: só os `_REQUIRED_CHARTS` precisam estar completos.
"""

from __future__ import annotations

from scripts.validate_cross import _REQUIRED_CHARTS, _cv10_charts_completeness


def _e5(**overrides) -> dict:
    charts = {c: {"context": "c", "conclusion": "f"} for c in _REQUIRED_CHARTS}
    charts.update(overrides)
    return {"narrativas": {"charts": charts}}


def test_opcional_vazio_nao_e_incompleto() -> None:
    """Obrigatórios completos + opcionais vazios (impostos_pj/wise) → CV10 passa."""
    r = _cv10_charts_completeness(
        _e5(
            impostos_pj={"context": "", "conclusion": ""},
            wise_fiscal_flags={"context": "", "conclusion": ""},
        )
    )
    assert r.passed is True
    assert r.severity == "info"


def test_obrigatorio_vazio_reprova_warning() -> None:
    """Um obrigatório presente mas vazio ainda é defeito real → warning."""
    r = _cv10_charts_completeness(_e5(score_gauge={"context": "", "conclusion": ""}))
    assert r.passed is False
    assert r.severity == "warning"
    assert "score_gauge" in r.details


def test_obrigatorio_faltando_reprova_error() -> None:
    charts = {
        c: {"context": "c", "conclusion": "f"} for c in _REQUIRED_CHARTS if c != "fluxo_mensal"
    }
    r = _cv10_charts_completeness({"narrativas": {"charts": charts}})
    assert r.passed is False
    assert r.severity == "error"


def test_todos_obrigatorios_completos_passa() -> None:
    r = _cv10_charts_completeness(_e5())
    assert r.passed is True
    assert r.severity == "info"
