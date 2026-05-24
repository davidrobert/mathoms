"""ChartsNarrator — gates de regressão para impostos_pj (ADR-236 §D4)."""

from __future__ import annotations

from typing import Any

import pytest

from pipeline.domain.services.narrativas import ChartsNarrator, NarrativasContext
from tests.test_e5n_builder_decomposition import _FAMILY_BASE, _build_metrics


def _narrate(metrics_override: dict[str, Any] | None = None) -> dict[str, Any]:
    ctx = NarrativasContext.from_family_config(_FAMILY_BASE)
    metrics = _build_metrics()
    if metrics_override is not None:
        metrics.update(metrics_override)
    return ChartsNarrator(ctx).narrate(metrics, _FAMILY_BASE, _RISCOS_FIXTURE, ["d1"])


_RISCOS_FIXTURE = [
    {"nome": "r1", "prob": "a", "impacto": "a"},
    {"nome": "r2", "prob": "a", "impacto": "a"},
]


_CASCATA_BASE: dict[str, Any] = {
    "regime_label": "fixture",
    "regime_nao_suportado": False,
    "motivo_nao_suportado": None,
    "receita_bruta": 240_000.0,
    "tributos_federais": 14_400.0,
    "iss_total": 0.0,
    "lucro_contabil_pj": 200_000.0,
    "pro_labore_bruto": 24_000.0,
    "inss_patronal": 0.0,
    "inss_empregado": 2_640.0,
    "irrf_pro_labore": 0.0,
    "lucros_distribuidos": 60_000.0,
    "renda_pf_tributavel_total": 60_000.0,
    "carga_total_pct": 0.06,
    "pgbl_base_anual": 60_000.0,
    "pgbl_limite_anual": 7_200.0,
    "pgbl_aplicavel": True,
    "pgbl_motivo_inaplicavel": None,
    "fator_r_pct": None,
    "fator_r_faixa": None,
    "fator_r_break_even_mensal": None,
    "triggers": [],
}


def _cascata(regime: str | None, **overrides: Any) -> dict[str, Any]:
    return {**_CASCATA_BASE, "regime": regime, **overrides}


def _section(
    regime: str | None = None,
    regime_label: str = "",
    cascata: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    return {
        "regime": regime,
        "regime_label": regime_label,
        "cascata": cascata or {},
        "contador_nome": kwargs.get("contador_nome"),
        "holding_prazo_meses": kwargs.get("holding_prazo_meses"),
        "_source": "db:business_profile_json + e3/e4/e1.6 derived",
    }


# ─── Gate N3: regression — string canned não pode aparecer ──────────────


_N3_FIXTURES: list[tuple[str, dict[str, Any]]] = [
    ("simples", _section("simples", "Simples Nacional — Anexo III", _cascata("simples"))),
    (
        "lucro_presumido",
        _section("lucro_presumido", "Lucro Presumido", _cascata("lucro_presumido")),
    ),
    ("mei", _section("mei", "MEI", _cascata("mei"))),
    (
        "lucro_real",
        _section(
            "lucro_real",
            "Lucro Real",
            _cascata("lucro_real", regime_nao_suportado=True, motivo_nao_suportado="lucro_real"),
        ),
    ),
    (
        "pendente",
        _section(
            None,
            "Perfil tributário incompleto",
            _cascata(None, regime_nao_suportado=True, motivo_nao_suportado="perfil_incompleto"),
        ),
    ),
]


@pytest.mark.parametrize("regime,section", _N3_FIXTURES)
def test_impostos_pj_no_hardcoded_lucro_presumido(regime: str, section: dict[str, Any]) -> None:
    """N3: string 'Lucro presumido (32%)' nunca aparece — confusão Simples × Presumido (ADR-236)."""
    out = _narrate({"tributario_section": section})
    text = (out["impostos_pj"]["context"] + " " + out["impostos_pj"]["conclusion"]).lower()
    assert "lucro presumido (32%)" not in text, f"N3 regression no regime {regime!r}"
    assert "× 0.32" not in text
    assert "x 0.32" not in text


# ─── Gate: ramificação por regime ───────────────────────────────────────


def test_impostos_pj_branches_simples():
    section = _section("simples", "Simples Nacional — Anexo III", _cascata("simples"))
    out = _narrate({"tributario_section": section})
    context = out["impostos_pj"]["context"]
    assert "Simples Nacional — Anexo III" in context
    assert "DAS" in context or "tributos federais" in context.lower()


def test_impostos_pj_branches_presumido_destaca_iss():
    cascata = _cascata("lucro_presumido", iss_total=12_000.0, fator_r_pct=None)
    section = _section("lucro_presumido", "Lucro Presumido", cascata)
    out = _narrate({"tributario_section": section})
    context = out["impostos_pj"]["context"]
    assert "Lucro Presumido" in context
    assert "ISS destacado" in context


def test_impostos_pj_branches_mei():
    section = _section("mei", "MEI", _cascata("mei", tributos_federais=958.80))
    out = _narrate({"tributario_section": section})
    context = out["impostos_pj"]["context"]
    assert "MEI" in context
    assert "DAS-MEI" in context


def test_impostos_pj_branches_lucro_real_unsupported():
    cascata = _cascata("lucro_real", regime_nao_suportado=True, motivo_nao_suportado="lucro_real")
    section = _section("lucro_real", "Lucro Real", cascata)
    out = _narrate({"tributario_section": section})
    assert "Lucro Real" in out["impostos_pj"]["context"]
    assert "V2" in out["impostos_pj"]["context"] or "contador" in out["impostos_pj"]["conclusion"]


def test_impostos_pj_perfil_pendente_when_section_missing():
    out = _narrate({"tributario_section": None})
    assert "Perfil tributário PJ pendente" in out["impostos_pj"]["context"]
    assert out["impostos_pj"]["conclusion"] == ""


def test_impostos_pj_perfil_pendente_when_regime_none():
    cascata = _cascata(None, regime_nao_suportado=True, motivo_nao_suportado="perfil_incompleto")
    section = _section(None, "Perfil tributário incompleto", cascata)
    out = _narrate({"tributario_section": section})
    assert "Perfil tributário PJ pendente" in out["impostos_pj"]["context"]


def test_impostos_pj_perfil_pendente_when_anexo_simples_missing():
    cascata = _cascata(
        "simples", regime_nao_suportado=True, motivo_nao_suportado="anexo_simples_pendente"
    )
    section = _section("simples", "Simples Nacional", cascata)
    out = _narrate({"tributario_section": section})
    assert "Perfil tributário PJ pendente" in out["impostos_pj"]["context"]


# ─── Gate: PGBL clause segue regras-as-code (ADR-236 §D2) ──────────────


def test_impostos_pj_pgbl_declaracao_simplificada_anula():
    cascata = _cascata(
        "simples",
        pgbl_aplicavel=False,
        pgbl_motivo_inaplicavel="declaracao_simplificada",
        pgbl_limite_anual=4_560.0,
    )
    section = _section("simples", "Simples Nacional — Anexo III", cascata)
    out = _narrate({"tributario_section": section})
    text = out["impostos_pj"]["conclusion"]
    assert "simplificada" in text.lower()
    assert "PGBL não dedutível" in text


def test_impostos_pj_pgbl_base_zerada():
    cascata = _cascata(
        "simples",
        pgbl_aplicavel=False,
        pgbl_motivo_inaplicavel="renda_tributavel_pf_zerada",
        pgbl_base_anual=0.0,
        pgbl_limite_anual=0.0,
    )
    section = _section("simples", "Simples Nacional — Anexo III", cascata)
    out = _narrate({"tributario_section": section})
    assert "Base PGBL ainda não detectada" in out["impostos_pj"]["conclusion"]


# ─── Gate: triggers de decisão aparecem na conclusion ───────────────────


def test_impostos_pj_triggers_listed_in_conclusion():
    cascata = _cascata(
        "simples",
        triggers=[
            {"code": "T1", "severity": "considere", "title": "...", "params": {}},
            {"code": "T3", "severity": "oportunidade", "title": "...", "params": {}},
        ],
    )
    section = _section("simples", "Simples Nacional — Anexo III", cascata)
    out = _narrate({"tributario_section": section})
    assert "T1" in out["impostos_pj"]["conclusion"]
    assert "T3" in out["impostos_pj"]["conclusion"]


def test_impostos_pj_no_triggers_omits_clause():
    section = _section("simples", "Simples Nacional — Anexo III", _cascata("simples", triggers=[]))
    out = _narrate({"tributario_section": section})
    assert "Sinalizadores ativos" not in out["impostos_pj"]["conclusion"]


# =============================================================================
# A17 L3 P5 — wise_fiscal_flags na ChartsNarrator output
# =============================================================================


def test_wise_fiscal_flags_vazio_quando_metrics_sem_flags():
    """Sem `wise_fiscal_flags` em metrics → narrativa vazia (context+conclusion+items)."""
    out = _narrate()
    assert "wise_fiscal_flags" in out
    assert out["wise_fiscal_flags"]["items"] == []
    assert out["wise_fiscal_flags"]["context"] == ""


_WISE_FLAGS_FIXTURE: list[dict[str, str]] = [
    {
        "code": "CBE",
        "severity": "info",
        "title": "Capital Brasileiro no Exterior (CBE BACEN)",
        "descricao": "Total de ativos no exterior: USD 1,500,000.00",
    },
    {
        "code": "CARNELEAO",
        "severity": "atencao",
        "title": "Carnê-leão mensal",
        "descricao": "Juros em USD do exterior — verifique recolhimento.",
    },
]


def test_wise_fiscal_flags_renderiza_items_com_codes():
    """Cada flag em metrics vira 1 item na narrativa."""
    out = _narrate({"wise_fiscal_flags": _WISE_FLAGS_FIXTURE})
    items = out["wise_fiscal_flags"]["items"]
    assert len(items) == 2
    assert {i["code"] for i in items} == {"CBE", "CARNELEAO"}
    assert "fact-check" in out["wise_fiscal_flags"]["context"].lower()
