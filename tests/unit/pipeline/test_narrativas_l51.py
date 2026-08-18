"""A40.l51 C4 — validador não obriga summary órfã."""

from __future__ import annotations

from pipeline.domain.services.narrativas.format_helpers import (
    DELIVERED_SUMMARY_KEYS,
    validate_narrativas,
)

_CHARTS = {
    key: {"context": "ctx", "conclusion": "conc"}
    for key in (
        "score_gauge",
        "patrimonio_doughnut",
        "alocacao_atual_vs_alvo",
        "fluxo_mensal",
        "receita_bar",
        "receita_despesa_mensal",
        "despesas_doughnut",
        "projecao_3cenarios",
        "waterfall_if",
        "renda_passiva",
        "top15_ativos",
        "impostos_pj",
        "cenarios_conjuge",
        "viagens",
        "bubble_riscos",
        "top5_decisoes",
    )
}


def _payload(*, s2: str | None = "") -> dict:
    summaries = {key: "ok" for key in DELIVERED_SUMMARY_KEYS}
    summaries["s2"] = s2
    return {
        "perfil_familia": {"left": "<p>ok</p>"},
        "summaries": summaries,
        "charts": _CHARTS,
    }


def test_s2_vazio_e_valido():
    ok, errors = validate_narrativas(_payload(s2=""))
    assert ok, errors


def test_s2_ausente_e_valido():
    payload = _payload()
    del payload["summaries"]["s2"]
    ok, errors = validate_narrativas(payload)
    assert ok, errors


def test_s1_vazio_continua_invalido():
    payload = _payload()
    payload["summaries"]["s1"] = ""
    ok, errors = validate_narrativas(payload)
    assert ok is False
    assert any("summaries.s1 is empty" in e for e in errors)
