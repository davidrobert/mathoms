"""Testes unitários do gerador determinístico de Suggestion (ADR-153).

Função pura: snapshot dict → list[SuggestionDraft]. Cada regra tem
felicidade + skip por dado faltante + dedup_key estável.

Valores fictícios — nunca dados reais (CLAUDE.md §Dados sensíveis).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pipeline.domain.services.suggestion_generator import (
    DISMISS_RESPECT_WINDOW_DAYS,
    SUGGESTION_CAP,
    SuggestionGenerator,
    SuggestionGeneratorConfig,
)
from pipeline.domain.types.suggestion import SuggestionDraft


@pytest.fixture
def gen() -> SuggestionGenerator:
    return SuggestionGenerator(SuggestionGeneratorConfig())


def test_constants_match_adr_153():
    assert SUGGESTION_CAP == 6
    assert DISMISS_RESPECT_WINDOW_DAYS == 90


def test_empty_snapshot_returns_no_drafts(gen):
    assert gen.generate({}) == []


def test_trs_desalinhada_warns_when_above_threshold(gen):
    snapshot = {"goals": {"taxa_retirada_efetiva_pct": 5.0}}  # 5% > 4% * 1.15 = 4.6%
    drafts = gen.generate(snapshot)
    kinds = [d.kind for d in drafts]
    assert "trs_desalinhada" in kinds
    d = next(d for d in drafts if d.kind == "trs_desalinhada")
    assert d.severity == "warning"
    assert d.section_id == "S7"


def test_trs_within_threshold_skips(gen):
    snapshot = {"goals": {"taxa_retirada_efetiva_pct": 4.5}}  # within 15% of 4%
    assert all(d.kind != "trs_desalinhada" for d in gen.generate(snapshot))


def test_reserva_insuficiente_danger_below_3_meses(gen):
    snapshot = {
        "reserva_emergencia": {"meses_cobertura": 1.5, "gap_brl": 9000.0},
    }
    drafts = gen.generate(snapshot)
    d = next(d for d in drafts if d.kind == "reserva_insuficiente")
    assert d.severity == "danger"
    assert d.section_id == "S2"
    assert d.amount_brl == Decimal("9000.00")


def test_reserva_warning_between_3_and_6_meses(gen):
    snapshot = {"reserva_emergencia": {"meses_cobertura": 4.0, "gap_brl": 5000.0}}
    drafts = gen.generate(snapshot)
    d = next(d for d in drafts if d.kind == "reserva_insuficiente")
    assert d.severity == "warning"


def test_reserva_at_target_skips(gen):
    snapshot = {"reserva_emergencia": {"meses_cobertura": 6.0, "gap_brl": 0.0}}
    assert all(d.kind != "reserva_insuficiente" for d in gen.generate(snapshot))


def test_alocacao_fora_alvo_pega_pior_desvio(gen):
    snapshot = {
        "investimentos": {
            "desvios_alvo": [
                {"classe": "renda_fixa", "desvio_pp": 5.0},
                {"classe": "renda_variavel", "desvio_pp": -15.0},
            ]
        }
    }
    drafts = gen.generate(snapshot)
    d = next(d for d in drafts if d.kind == "alocacao_fora_alvo")
    assert "renda_variavel" in d.title
    assert "aumentar" in d.title.lower()


def test_alocacao_dentro_da_tolerancia_skips(gen):
    snapshot = {
        "investimentos": {
            "desvios_alvo": [{"classe": "X", "desvio_pp": 5.0}]  # 5pp < 10pp
        }
    }
    assert all(d.kind != "alocacao_fora_alvo" for d in gen.generate(snapshot))


def test_aporte_abaixo_meta_warning(gen):
    snapshot = {"fluxo_caixa": {"aporte_medio_3m": 1000.0, "aporte_meta_mensal": 2000.0}}
    drafts = gen.generate(snapshot)
    d = next(d for d in drafts if d.kind == "aporte_abaixo_meta")
    assert d.severity == "warning"
    assert d.amount_brl == Decimal("1000.00")


def test_aporte_em_dia_skips(gen):
    snapshot = {"fluxo_caixa": {"aporte_medio_3m": 1500.0, "aporte_meta_mensal": 2000.0}}
    assert all(d.kind != "aporte_abaixo_meta" for d in gen.generate(snapshot))


def test_dolarizacao_atrasada_quando_drift_acima_threshold(gen):
    snapshot = {"dolarizacao": {"cobertura_pct": 20.0, "meta_pct": 50.0}}
    drafts = gen.generate(snapshot)
    d = next(d for d in drafts if d.kind == "dolarizacao_atrasada")
    assert d.section_id == "U1"
    assert "30pp" in d.title


def test_dolarizacao_dentro_drift_skips(gen):
    snapshot = {"dolarizacao": {"cobertura_pct": 40.0, "meta_pct": 50.0}}
    assert all(d.kind != "dolarizacao_atrasada" for d in gen.generate(snapshot))


def test_ranking_severity_first_then_amount(gen):
    """5 regras dispara, todas → ordem deve ser danger > warning > info."""
    snapshot = {
        "goals": {"taxa_retirada_efetiva_pct": 5.0},  # warning
        "reserva_emergencia": {"meses_cobertura": 1.0, "gap_brl": 9000.0},  # danger
        "investimentos": {"desvios_alvo": [{"classe": "X", "desvio_pp": 30.0}]},  # info
        "fluxo_caixa": {"aporte_medio_3m": 100.0, "aporte_meta_mensal": 1000.0},  # warning
        "dolarizacao": {"cobertura_pct": 0.0, "meta_pct": 50.0},  # info
    }
    drafts = gen.generate(snapshot)
    severities = [d.severity for d in drafts]
    severity_rank = {"danger": 3, "warning": 2, "info": 1}
    assert all(
        severity_rank[severities[i]] >= severity_rank[severities[i + 1]]
        for i in range(len(severities) - 1)
    )


def test_cap_truncates_at_six(gen):
    """Se 5 regras dispararem, cap=6 não trunca; teste defensivo."""
    snapshot = {
        "goals": {"taxa_retirada_efetiva_pct": 5.0},
        "reserva_emergencia": {"meses_cobertura": 1.0, "gap_brl": 9000.0},
        "investimentos": {"desvios_alvo": [{"classe": "X", "desvio_pp": 30.0}]},
        "fluxo_caixa": {"aporte_medio_3m": 100.0, "aporte_meta_mensal": 1000.0},
        "dolarizacao": {"cobertura_pct": 0.0, "meta_pct": 50.0},
    }
    drafts = gen.generate(snapshot)
    assert len(drafts) <= SUGGESTION_CAP


def test_dedup_key_is_stable_across_runs(gen):
    snapshot = {"reserva_emergencia": {"meses_cobertura": 1.5, "gap_brl": 9000.0}}
    d1 = gen.generate(snapshot)[0]
    d2 = gen.generate(snapshot)[0]
    assert d1.dedup_key == d2.dedup_key


def test_dedup_key_changes_with_material_diff(gen):
    """Reserva 1.5 meses (bucket 1to3) vs 4.0 meses (bucket 3to6) → keys diferentes."""
    s1 = {"reserva_emergencia": {"meses_cobertura": 1.5, "gap_brl": 9000.0}}
    s2 = {"reserva_emergencia": {"meses_cobertura": 4.0, "gap_brl": 5000.0}}
    d1 = next(d for d in gen.generate(s1) if d.kind == "reserva_insuficiente")
    d2 = next(d for d in gen.generate(s2) if d.kind == "reserva_insuficiente")
    assert d1.dedup_key != d2.dedup_key


def test_dedup_key_stable_for_small_drift(gen):
    """TRS 4.8% vs 4.95% — mesmo bucket 0.5pp → mesma key."""
    s1 = {"goals": {"taxa_retirada_efetiva_pct": 4.8}}
    s2 = {"goals": {"taxa_retirada_efetiva_pct": 4.95}}
    d1 = next(d for d in gen.generate(s1) if d.kind == "trs_desalinhada")
    d2 = next(d for d in gen.generate(s2) if d.kind == "trs_desalinhada")
    assert d1.dedup_key == d2.dedup_key


def test_malformed_snapshot_does_not_crash(gen):
    snapshot = {
        "goals": "not a dict",
        "reserva_emergencia": [],
        "investimentos": None,
        "fluxo_caixa": {"aporte_medio_3m": "abc"},
    }
    # Defensive: skip silenciosamente, sem raise.
    drafts = gen.generate(snapshot)
    assert isinstance(drafts, list)


def test_drafts_are_immutable():
    d = SuggestionDraft(
        section_id="S2",
        kind="reserva_insuficiente",
        severity="warning",
        title="t",
        rationale="r",
        dedup_key="abcd1234",
    )
    with pytest.raises((AttributeError, Exception)):  # frozen dataclass
        d.title = "outro"  # type: ignore[misc]


# =============================================================================
# Onda 10 #5 — body_md enriquecido nas regras 2 e 3
# =============================================================================


def test_reserva_rationale_enriquecido_com_gap_e_aporte(gen):
    """Regra 2 — gap + aporte mensal + ETA aparecem no rationale."""
    snapshot = {
        "reserva_emergencia": {"meses_cobertura": 2.0, "gap_brl": 9000.0},
        "fluxo_caixa": {"aporte_meta_mensal": 3000.0},
    }
    d = next(d for d in gen.generate(snapshot) if d.kind == "reserva_insuficiente")
    assert "R$ 9.000,00" in d.rationale  # gap formatado BR
    assert "R$ 3.000,00" in d.rationale  # aporte mensal projetado
    assert "~3 meses" in d.rationale  # ETA = 9000 / 3000 = 3
    assert "Próximo passo" in d.rationale  # call-to-action explícito


def test_reserva_rationale_degrada_quando_aporte_ausente(gen):
    """Sem fluxo_caixa, ainda funciona — só perde a parte de ETA."""
    snapshot = {
        "reserva_emergencia": {"meses_cobertura": 1.0, "gap_brl": 9000.0},
    }
    d = next(d for d in gen.generate(snapshot) if d.kind == "reserva_insuficiente")
    assert "R$ 9.000,00" in d.rationale  # gap ainda aparece
    assert "Próximo passo" not in d.rationale  # CTA é condicional ao aporte


_ALOCACAO_FULL_SNAPSHOT = {
    "investimentos": {
        "desvios_alvo": [
            {"classe": "renda_variavel", "desvio_pp": -15.0, "atual_pct": 25.0, "alvo_pct": 40.0},
            {"classe": "renda_fixa", "desvio_pp": 15.0, "atual_pct": 75.0, "alvo_pct": 60.0},
        ]
    },
    "fluxo_caixa": {"aporte_meta_mensal": 2500.0},
}


def test_alocacao_rationale_inclui_atual_alvo_quando_disponivel(gen):
    d = next(d for d in gen.generate(_ALOCACAO_FULL_SNAPSHOT) if d.kind == "alocacao_fora_alvo")
    assert "renda_variavel" in d.rationale
    assert "atual 25.0%" in d.rationale and "alvo 40.0%" in d.rationale
    assert "R$ 2.500,00" in d.rationale
    assert "| Classe | Atual | Alvo | Δ |" in d.rationale
    assert "renda_fixa" in d.rationale


def test_alocacao_rationale_degrada_sem_pcts(gen):
    """Snapshot legado (só desvio_pp) não quebra — cai no rationale curto."""
    snapshot = {
        "investimentos": {"desvios_alvo": [{"classe": "renda_variavel", "desvio_pp": -15.0}]}
    }
    d = next(d for d in gen.generate(snapshot) if d.kind == "alocacao_fora_alvo")
    assert "renda_variavel" in d.rationale
    assert "atual" not in d.rationale  # não inventa números
    assert "| Classe |" not in d.rationale  # sem tabela quando dados faltam
