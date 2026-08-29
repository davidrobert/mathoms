"""Testes unitários do gerador determinístico de Suggestion (ADR-153).

Função pura: snapshot dict → list[SuggestionDraft]. Cada regra tem
felicidade + skip por dado faltante + dedup_key estável.

Valores fictícios — nunca dados reais (CLAUDE.md §Dados sensíveis).
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

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


def test_constants_match_adr_161():
    # ADR-161 (Onda 8): cap sobe de 6 → 8 com 11 regras candidatas.
    assert SUGGESTION_CAP == 8
    assert DISMISS_RESPECT_WINDOW_DAYS == 90


def test_empty_snapshot_returns_no_drafts(gen):
    assert gen.generate({}) == []


def test_nenhuma_sugestao_compara_trs_com_alvo(gen):
    """[[ADR-191]] §D6 §Emenda 2026-08-29 — gate por AUSÊNCIA, no terceiro consumidor."""
    # O Aceite do D6 fechava em "nos dois consumidores" e `rule_trs_desalinhada` era o
    # terceiro, com `section_id="S7"` — dentro do escopo declarado, fora do que ele mediu.
    # O cenário que ANTES disparava: 5% > 4% × 1,15 e progresso IF ≥ 50%.
    drafts = gen.generate({"goals": {"taxa_retirada_efetiva_pct": 5.0, "if_pct": 60.0}})
    assert "trs_desalinhada" not in [d.kind for d in drafts]
    proibidos = ("taxa de retirada", "retirada segura", "% ao ano")
    for d in drafts:
        texto = f"{d.title} {d.rationale}".lower()
        assert not [t for t in proibidos if t in texto], f"{d.kind} prescreve sobre TRS"


def test_trs_within_threshold_skips(gen):
    snapshot = {
        "goals": {"taxa_retirada_efetiva_pct": 4.5, "if_pct": 60.0},
    }  # within 15% of 4%
    assert all(d.kind != "trs_desalinhada" for d in gen.generate(snapshot))


def test_trs_desalinhada_silent_in_acumulacao_phase(gen):
    """A8.3 — em acumulação (if_pct < 50) TRS alta não dispara warning."""
    snapshot = {
        "goals": {"taxa_retirada_efetiva_pct": 6.0, "if_pct": 25.0},
    }  # TRS efetiva passa do threshold 4.6% mas if_pct < 50.
    drafts = gen.generate(snapshot)
    assert all(d.kind != "trs_desalinhada" for d in drafts)


def test_reserva_insuficiente_danger_below_3_meses(gen):
    snapshot = {
        "reserva_emergencia": {"cobertura_meses": 1.5, "gap_brl": 9000.0},
    }
    drafts = gen.generate(snapshot)
    d = next(d for d in drafts if d.kind == "reserva_insuficiente")
    assert d.severity == "danger"
    assert d.section_id == "S2"
    assert d.amount_brl == Decimal("9000.00")


def test_reserva_warning_between_3_and_6_meses(gen):
    snapshot = {"reserva_emergencia": {"cobertura_meses": 4.0, "gap_brl": 5000.0}}
    drafts = gen.generate(snapshot)
    d = next(d for d in drafts if d.kind == "reserva_insuficiente")
    assert d.severity == "warning"


def test_reserva_at_target_skips(gen):
    snapshot = {"reserva_emergencia": {"cobertura_meses": 6.0, "gap_brl": 0.0}}
    assert all(d.kind != "reserva_insuficiente" for d in gen.generate(snapshot))


# RV3-09 (A40.l5): a regra lia `meses_cobertura`, chave que produtor nenhum
# emite, e devolvia None para todo workspace — regra de segurança morta em
# produção. Os três testes acima ficaram VERDES o tempo todo porque a fixture
# escrita à mão repetia a mesma crença errada do código. Por isso o teste
# abaixo é alimentado pelo PRODUTOR (payload real do snapshot de dogfood), não
# por dict literal: é o único que teria falhado.
_DOGFOOD_SNAPSHOT = (
    Path(__file__).resolve().parent.parent
    / "backend"
    / "tests"
    / "snapshots"
    / "dogfood_view_model.json"
)


def _reserva_do_produtor() -> dict:
    """Bloco `reserva_emergencia` como o E5 realmente o emite."""
    payload = json.loads(_DOGFOOD_SNAPSHOT.read_text(encoding="utf-8"))
    return payload["reserva_emergencia"]


def test_reserva_le_a_chave_que_o_produtor_emite():
    """Trava a chave contra o produtor: `cobertura_meses` existe, o alias não."""
    reserva = _reserva_do_produtor()
    assert "cobertura_meses" in reserva
    assert "meses_cobertura" not in reserva, "produtor mudou de chave; a regra vai morrer de novo"


def test_reserva_insuficiente_dispara_sobre_payload_real(gen):
    """Com o payload do produtor a regra tem de opinar — antes retornava None."""
    reserva = {**_reserva_do_produtor(), "cobertura_meses": 1.5, "gap_brl": 9000.0}
    drafts = gen.generate({"reserva_emergencia": reserva})
    assert any(
        d.kind == "reserva_insuficiente" for d in drafts
    ), "regra inerte sobre o shape real do E5 (RV3-09)"


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


def test_dolarizacao_atrasada_removed_from_all_rules():
    """FP-003: regra removida (ADR-168 — Modo USA removido)."""
    from pipeline.domain.services.suggestion_rules import ALL_RULES
    from pipeline.domain.types.suggestion import KIND_TO_CATEGORY, VALID_KINDS

    rule_names = {r.__name__ for r in ALL_RULES}
    assert "rule_dolarizacao_atrasada" not in rule_names
    assert "dolarizacao_atrasada" not in KIND_TO_CATEGORY
    assert "dolarizacao_atrasada" not in VALID_KINDS


def test_dolarizacao_snapshot_silently_ignored(gen):
    """FP-003: snapshot com `dolarizacao` não dispara nada (regra removida)."""
    snapshot = {"dolarizacao": {"cobertura_pct": 20.0, "meta_pct": 50.0}}
    drafts = gen.generate(snapshot)
    assert all(d.kind != "dolarizacao_atrasada" for d in drafts)


def test_ranking_severity_first_then_amount(gen):
    """5 regras dispara, todas → ordem deve ser danger > warning > info."""
    snapshot = {
        "goals": {
            "taxa_retirada_efetiva_pct": 5.0,
            "if_pct": 60.0,  # A8.3: TRS desalinhada exige fase IF.
        },  # warning
        "reserva_emergencia": {"cobertura_meses": 1.0, "gap_brl": 9000.0},  # danger
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
        "goals": {"taxa_retirada_efetiva_pct": 5.0, "if_pct": 60.0},
        "reserva_emergencia": {"cobertura_meses": 1.0, "gap_brl": 9000.0},
        "investimentos": {"desvios_alvo": [{"classe": "X", "desvio_pp": 30.0}]},
        "fluxo_caixa": {"aporte_medio_3m": 100.0, "aporte_meta_mensal": 1000.0},
        "dolarizacao": {"cobertura_pct": 0.0, "meta_pct": 50.0},
    }
    drafts = gen.generate(snapshot)
    assert len(drafts) <= SUGGESTION_CAP


def test_dedup_key_is_stable_across_runs(gen):
    snapshot = {"reserva_emergencia": {"cobertura_meses": 1.5, "gap_brl": 9000.0}}
    d1 = gen.generate(snapshot)[0]
    d2 = gen.generate(snapshot)[0]
    assert d1.dedup_key == d2.dedup_key


def test_dedup_key_changes_with_material_diff(gen):
    """Reserva 1.5 meses (bucket 1to3) vs 4.0 meses (bucket 3to6) → keys diferentes."""
    s1 = {"reserva_emergencia": {"cobertura_meses": 1.5, "gap_brl": 9000.0}}
    s2 = {"reserva_emergencia": {"cobertura_meses": 4.0, "gap_brl": 5000.0}}
    d1 = next(d for d in gen.generate(s1) if d.kind == "reserva_insuficiente")
    d2 = next(d for d in gen.generate(s2) if d.kind == "reserva_insuficiente")
    assert d1.dedup_key != d2.dedup_key


def test_dedup_key_stable_for_small_drift(gen):
    """Mesmo bucket → mesma key. Veículo trocado de `trs_desalinhada` (removida em
    2026-08-29) para `taxa_poupanca_caindo`: o que se mede é a estabilidade do bucket,
    não a regra."""

    def _snap(atual: float) -> dict:
        return {"fluxo_caixa": {"taxa_poupanca_trimestral_historico": [30.0, 24.0, 18.0, atual]}}

    # 12,0 e 12,4 caem no mesmo bucket (step 2,5) E ambos disparam: 13,0 não serviria,
    # porque 18→13 é queda de exatamente 5,0pp e a regra exige MAIS que o limiar.
    d1 = next(d for d in gen.generate(_snap(12.0)) if d.kind == "taxa_poupanca_caindo")
    d2 = next(d for d in gen.generate(_snap(12.4)) if d.kind == "taxa_poupanca_caindo")
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
        "reserva_emergencia": {"cobertura_meses": 2.0, "gap_brl": 9000.0},
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
        "reserva_emergencia": {"cobertura_meses": 1.0, "gap_brl": 9000.0},
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


# =============================================================================
# ADR-161 (Onda 8) — 6 regras canônicas v2 (Cerbasi/AUVP/Perini completos)
# =============================================================================


def test_category_is_inferred_from_kind():
    """Category é auto-derivada via KIND_TO_CATEGORY se não explicitada."""
    d = SuggestionDraft(
        section_id="S2",
        kind="reserva_insuficiente",
        severity="warning",
        title="t",
        rationale="r",
        dedup_key="abcd1234",
    )
    assert d.category == "protecao"


def test_endividamento_perigoso_pct_acima_30(gen):
    """Cerbasi/AUVP — dívidas > 30% do bruto dispara `danger`."""
    snapshot = {"endividamento": {"percentual_patrimonio": 35.0, "total_dividas": 350_000.0}}
    drafts = gen.generate(snapshot)
    d = next(d for d in drafts if d.kind == "endividamento_perigoso")
    assert d.severity == "danger"
    assert d.category == "endividamento"
    assert d.amount_brl == Decimal("350000.00")


def test_endividamento_perigoso_carry_negativo(gen):
    """Custo > retorno esperado dispara mesmo com %patrimônio baixo."""
    snapshot = {
        "endividamento": {
            "percentual_patrimonio": 10.0,  # baixo
            "total_dividas": 50_000.0,
            "custo_medio_pct_aa": 18.0,  # alto
        },
        "goals": {"retorno_esperado_pct_aa": 8.0},  # menor que custo
    }
    drafts = gen.generate(snapshot)
    d = next(d for d in drafts if d.kind == "endividamento_perigoso")
    assert d.severity == "danger"
    assert "custo médio" in d.rationale.lower() or "carrego" in d.rationale.lower()


def test_endividamento_dentro_limite_skips(gen):
    snapshot = {"endividamento": {"percentual_patrimonio": 15.0, "total_dividas": 50_000.0}}
    assert all(d.kind != "endividamento_perigoso" for d in gen.generate(snapshot))


def test_taxa_poupanca_caindo_2_quedas_consecutivas(gen):
    """Cerbasi · comportamental — duas quedas >5pp consecutivas."""
    # 4 trimestres: 30% → 24% (-6pp) → 18% (-6pp) → 17% (-1pp)
    # Janela analisada: últimos 3 trimestres (consecutive_quarters+1=3) = [24, 18, 17]
    # Quedas: 24→18 = -6 (queda) ✓, 18→17 = -1 (não queda)
    # → drops_consecutive sai 1, depois reset a 0 → não dispara
    # Quero exatamente 2 consecutivas → [30, 24, 18]
    snapshot = {
        "fluxo_caixa": {
            "taxa_poupanca_trimestral_historico": [30.0, 24.0, 18.0],
        }
    }
    drafts = gen.generate(snapshot)
    d = next(d for d in drafts if d.kind == "taxa_poupanca_caindo")
    assert d.severity == "warning"
    assert d.category == "comportamental"


def test_taxa_poupanca_uma_queda_so_skips(gen):
    """1 queda + estável → não dispara (precisa 2 consecutivas)."""
    snapshot = {
        "fluxo_caixa": {
            "taxa_poupanca_trimestral_historico": [30.0, 24.0, 23.0],
        }
    }
    assert all(d.kind != "taxa_poupanca_caindo" for d in gen.generate(snapshot))


def test_taxa_poupanca_historico_curto_skips(gen):
    """Histórico < 3 trimestres → skip silencioso."""
    snapshot = {"fluxo_caixa": {"taxa_poupanca_trimestral_historico": [30.0, 24.0]}}
    assert all(d.kind != "taxa_poupanca_caindo" for d in gen.generate(snapshot))


# O snapshot abaixo é o que a regra deletada exigia; ele nunca existiu no E5 —
# a chave canônica de proteção é `protecao_patrimonial` (ADR-240), e o produtor
# único do conselho é `pontos_urgentes_analyzer._seguro_vida_item`.
def test_seguros_nao_tem_produtor_deterministico(gen):
    """FP-010 (ADR-161 §Emenda 2026-08-11) — regra removida, não re-adicionada."""
    snapshot = {
        "fluxo_caixa": {"renda_pj_mensal": 80_000.0},
        "seguros": {"vida_invalidez": False},
    }
    assert all(d.kind != "seguros_insuficientes" for d in gen.generate(snapshot))


def test_concentracao_instituicao_acima_40_pct(gen):
    """AUVP — algum banco > 40% do investível."""
    snapshot = {
        "patrimonio": {
            "por_instituicao": {
                "btgpactual": 600_000.0,  # 60% — fora do limite
                "itau": 200_000.0,
                "xpinvestimentos": 200_000.0,
            }
        }
    }
    drafts = gen.generate(snapshot)
    d = next(d for d in drafts if d.kind == "concentracao_instituicao")
    assert d.severity == "warning"
    assert "btgpactual" in d.title.lower()
    assert d.category == "carteira"


def test_concentracao_distribuida_skips(gen):
    snapshot = {
        "patrimonio": {
            "por_instituicao": {
                "btgpactual": 350_000.0,  # 35% — dentro do limite
                "itau": 350_000.0,
                "xpinvestimentos": 300_000.0,
            }
        }
    }
    assert all(d.kind != "concentracao_instituicao" for d in gen.generate(snapshot))


def test_lifestyle_creep_acima_inflacao_x1_5(gen):
    """Cerbasi/Perini — despesa essencial cresce 12% em 6m vs 5% inflação (×1.5=7.5%)."""
    snapshot = {
        "fluxo_caixa": {
            "despesa_essencial_historico": [
                10_000.0,
                10_500.0,
                10_800.0,
                11_000.0,
                11_300.0,
                11_200.0,  # +12% vs primeiro
            ]
        },
        "inflacao": {"acumulada_pct_no_periodo": 5.0},  # 5% × 1.5 = 7.5pp threshold
    }
    drafts = gen.generate(snapshot)
    d = next(d for d in drafts if d.kind == "lifestyle_creep")
    assert d.severity == "warning"
    assert d.category == "comportamental"


def test_lifestyle_creep_dentro_inflacao_skips(gen):
    snapshot = {
        "fluxo_caixa": {
            "despesa_essencial_historico": [
                10_000.0,
                10_100.0,
                10_200.0,
                10_300.0,
                10_400.0,
                10_500.0,  # +5% vs primeiro
            ]
        },
        "inflacao": {"acumulada_pct_no_periodo": 5.0},
    }
    assert all(d.kind != "lifestyle_creep" for d in gen.generate(snapshot))


def test_renda_passiva_real_baixa_progresso_alto_renda_baixa(gen):
    """Perini "300" — IF 60% mas renda passiva cobre só 20% do custo."""
    snapshot = {
        "goals": {"progresso_if_pct": 60.0},
        "fluxo_caixa": {
            "renda_passiva_mensal_atual": 4_000.0,
            "despesa_mensal_media": 20_000.0,  # 20% cobertura
        },
    }
    drafts = gen.generate(snapshot)
    d = next(d for d in drafts if d.kind == "renda_passiva_real_baixa")
    assert d.severity == "info"
    assert d.category == "alvo_if"


def test_renda_passiva_progresso_baixo_skips(gen):
    """IF < 50% → skip (alvo Perini só faz sentido após metade do plano)."""
    snapshot = {
        "goals": {"progresso_if_pct": 30.0},
        "fluxo_caixa": {
            "renda_passiva_mensal_atual": 1_000.0,
            "despesa_mensal_media": 20_000.0,
        },
    }
    assert all(d.kind != "renda_passiva_real_baixa" for d in gen.generate(snapshot))


def test_renda_passiva_cobertura_acima_meta_skips(gen):
    snapshot = {
        "goals": {"progresso_if_pct": 70.0},
        "fluxo_caixa": {
            "renda_passiva_mensal_atual": 8_000.0,
            "despesa_mensal_media": 20_000.0,  # 40% cobertura — acima do alvo 30%
        },
    }
    assert all(d.kind != "renda_passiva_real_baixa" for d in gen.generate(snapshot))


def test_all_v2_rules_have_dedup_key_stable_across_runs(gen):
    """Estabilidade de dedup_key para todas as regras v2 (idempotência ADR-153)."""
    snapshot = {
        "endividamento": {"percentual_patrimonio": 35.0, "total_dividas": 350_000.0},
        "fluxo_caixa": {
            "taxa_poupanca_trimestral_historico": [30.0, 24.0, 18.0],
            "despesa_essencial_historico": [10_000, 10_500, 10_800, 11_000, 11_300, 11_200],
            "renda_passiva_mensal_atual": 4_000.0,
            "despesa_mensal_media": 20_000.0,
        },
        "patrimonio": {"por_instituicao": {"btgpactual": 600_000.0, "itau": 200_000.0}},
        "inflacao": {"acumulada_pct_no_periodo": 5.0},
        "goals": {"progresso_if_pct": 60.0},
    }
    drafts1 = {d.kind: d.dedup_key for d in gen.generate(snapshot)}
    drafts2 = {d.kind: d.dedup_key for d in gen.generate(snapshot)}
    assert drafts1 == drafts2
    # As 5 regras v2 vivas dispararam (seguros_insuficientes removida — FP-010).
    assert "endividamento_perigoso" in drafts1
    assert "taxa_poupanca_caindo" in drafts1
    assert "concentracao_instituicao" in drafts1
    assert "lifestyle_creep" in drafts1
    assert "renda_passiva_real_baixa" in drafts1


def test_all_9_rules_can_coexist_under_cap(gen):
    """Smoke: 9 regras possíveis (FP-003 dolarizacao, FP-010 seguros), cap=8 trunca."""
    snapshot = {
        # v1
        "goals": {
            "taxa_retirada_efetiva_pct": 5.0,
            "if_pct": 60.0,  # A8.3: trs_desalinhada exige fase IF.
            "progresso_if_pct": 60.0,  # alvo da regra renda_passiva_real_baixa.
            "retorno_esperado_pct_aa": 8.0,
        },
        "reserva_emergencia": {"cobertura_meses": 1.0, "gap_brl": 9000.0},
        "investimentos": {"desvios_alvo": [{"classe": "X", "desvio_pp": 30.0}]},
        "fluxo_caixa": {
            "aporte_medio_3m": 100.0,
            "aporte_meta_mensal": 1000.0,
            "taxa_poupanca_trimestral_historico": [30.0, 24.0, 18.0],
            "renda_pj_mensal": 80_000.0,
            "despesa_essencial_historico": [10_000, 10_500, 10_800, 11_000, 11_300, 11_200],
            "renda_passiva_mensal_atual": 4_000.0,
            "despesa_mensal_media": 20_000.0,
        },
        "dolarizacao": {"cobertura_pct": 0.0, "meta_pct": 50.0},
        # v2
        "endividamento": {
            "percentual_patrimonio": 35.0,
            "total_dividas": 350_000.0,
            "custo_medio_pct_aa": 18.0,
        },
        "patrimonio": {"por_instituicao": {"btgpactual": 600_000.0, "itau": 200_000.0}},
        "inflacao": {"acumulada_pct_no_periodo": 5.0},
    }
    drafts = gen.generate(snapshot)
    assert len(drafts) == SUGGESTION_CAP  # ranqueado e truncado em 8
    # Todas dangers vêm primeiro
    severities = [d.severity for d in drafts]
    severity_rank = {"danger": 3, "warning": 2, "info": 1}
    assert all(
        severity_rank[severities[i]] >= severity_rank[severities[i + 1]]
        for i in range(len(severities) - 1)
    )
