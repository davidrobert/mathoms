"""Tests — ``e5_serialization`` (Sessão A5d)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.e5_serialization import (  # noqa: E402
    E5_ARTIFACT_FILENAME,
    E5_ARTIFACT_KEY,
    E5_OUTPUT_STAGE,
    E5OutputInputs,
    SanityWarning,
    build_alertas,
    build_default_tarefas,
    build_default_tarefas_status,
    build_e5_output,
    run_sanity_checks,
)


def _inputs(**overrides) -> E5OutputInputs:
    base = {
        "periodo_dados": "2026-01 a 2026-12",
        "data_analise": "2026-04-19",
        "patrimonio": {"bruto": 1_000_000, "liquido": 800_000},
        "goals": {"if_meta": 5_000_000, "if_pct": 20},
        "fluxo": {"receita_total": 100_000, "despesa_total": 60_000},
        "ratios": {"taxa_poupanca_recorrente_pct": 40, "rentabilidade_pct": "N/D"},
        "score": {"valor": 7.5, "classificacao": "Bom"},
        "orcamento": {"total": 5_000},
        "reserva": {"cobertura_meses": 12},
        "endividamento": {"total_dividas": 200_000},
        "previdencia": {"status": "N/D"},
        "pontos_fortes": [{"titulo": "Score Positivo"}],
        "pontos_urgentes": [
            {"acao": "Reforçar reserva", "prioridade": "Alta", "prazo": "Imediato", "impacto": "X"},
        ],
        "investimentos_classes": {"total": 500_000, "tabela_classes": []},
        "equilibrio_cerbasi": {"classificacao": "Equilibrado"},
        "consumo": {"total_pontuais": 10_000},
        "diagnostico": [{"padrao": "Disciplina"}],
        "cenarios_conjuge": {"cenarios": []},
    }
    base.update(overrides)
    return E5OutputInputs(**base)


# =============================================================================
# Constantes
# =============================================================================


class TestConstants:
    def test_stage_key_and_filename(self):
        assert E5_OUTPUT_STAGE == "E5"
        assert E5_ARTIFACT_KEY == "analise_financeira"
        assert E5_ARTIFACT_FILENAME == "analise_financeira-5_analysis.json"


# =============================================================================
# Sanity checks
# =============================================================================


class TestSanityChecks:
    def test_no_warnings_quando_valores_saudaveis(self):
        warnings = run_sanity_checks(
            patrimonio={"bruto": 1_000_000},
            fluxo={"receita_total": 100_000, "despesa_total": 60_000},
            ratios={"taxa_poupanca_recorrente_pct": 40, "taxa_endividamento_pct": 10},
            goals={"if_pct": 20},
            score={"valor": 7.5},
        )
        assert warnings == []

    def test_patrimonio_negativo(self):
        warnings = run_sanity_checks(
            patrimonio={"bruto": -100},
            fluxo={"receita_total": 0, "despesa_total": 0},
            ratios={"taxa_poupanca_recorrente_pct": 0, "taxa_endividamento_pct": 0},
            goals={"if_pct": 0},
            score={"valor": 5},
        )
        assert len(warnings) == 1
        assert warnings[0].field == "patrimonio.bruto"

    def test_receita_e_despesa_negativas(self):
        warnings = run_sanity_checks(
            patrimonio={"bruto": 1000},
            fluxo={"receita_total": -100, "despesa_total": -50},
            ratios={"taxa_poupanca_recorrente_pct": 0},
            goals={},
            score={"valor": 5},
        )
        fields = {w.field for w in warnings}
        assert "fluxo.receita_total" in fields
        assert "fluxo.despesa_total" in fields

    def test_taxa_poupanca_fora_range(self):
        warnings = run_sanity_checks(
            patrimonio={"bruto": 1000},
            fluxo={"receita_total": 0, "despesa_total": 0},
            ratios={"taxa_poupanca_recorrente_pct": 150},
            goals={},
            score={"valor": 5},
        )
        assert any(w.field == "ratios.taxa_poupanca_recorrente_pct" for w in warnings)

    def test_taxa_poupanca_string_nao_dispara(self):
        warnings = run_sanity_checks(
            patrimonio={"bruto": 1000},
            fluxo={"receita_total": 0, "despesa_total": 0},
            ratios={"taxa_poupanca_recorrente_pct": "N/D"},
            goals={},
            score={"valor": 5},
        )
        assert not any(w.field == "ratios.taxa_poupanca_recorrente_pct" for w in warnings)

    def test_endividamento_acima_200pct(self):
        warnings = run_sanity_checks(
            patrimonio={"bruto": 1000},
            fluxo={"receita_total": 0, "despesa_total": 0},
            ratios={"taxa_endividamento_pct": 250, "taxa_poupanca_recorrente_pct": 0},
            goals={},
            score={"valor": 5},
        )
        assert any(w.field == "ratios.taxa_endividamento_pct" for w in warnings)

    def test_endividamento_usa_chave_canonica_do_ratios_calculator(self):
        # Regressão: warning lia chave órfã `endividamento_pct`, sempre-0 silencioso.
        from pipeline.domain.services.ratios_calculator import FinancialRatios

        ratios = FinancialRatios(0.0, 0.0, 250.0, 0.0).to_legacy_dict()
        warnings = run_sanity_checks(
            patrimonio={"bruto": 1000},
            fluxo={"receita_total": 0, "despesa_total": 0},
            ratios=ratios,
            goals={},
            score={"valor": 5},
        )
        assert any(w.field == "ratios.taxa_endividamento_pct" for w in warnings)

    def test_endividamento_chave_orfa_legada_nao_dispara(self):
        """Regressão — proteção explícita contra reintrodução do bug:
        chave legada `endividamento_pct` (sem prefixo `taxa_`) NÃO deve
        ser lida; only the canonical `taxa_endividamento_pct` is honored.
        """
        warnings = run_sanity_checks(
            patrimonio={"bruto": 1000},
            fluxo={"receita_total": 0, "despesa_total": 0},
            ratios={"endividamento_pct": 250, "taxa_poupanca_recorrente_pct": 0},
            goals={},
            score={"valor": 5},
        )
        assert not any("endividamento" in w.field for w in warnings)

    def test_score_fora_range(self):
        warnings = run_sanity_checks(
            patrimonio={"bruto": 1000},
            fluxo={"receita_total": 0, "despesa_total": 0},
            ratios={"taxa_poupanca_recorrente_pct": 0},
            goals={},
            score={"valor": 15},
        )
        assert any(w.field == "score.valor" for w in warnings)


# =============================================================================
# Tarefas fallback
# =============================================================================


class TestTarefasFallback:
    def test_default_tarefas_from_pontos_urgentes(self):
        urgentes = [
            {"acao": "Reforçar reserva", "prioridade": "Alta", "prazo": "Imediato", "impacto": "X"},
            {"acao": "Reduzir dívida", "prioridade": "Média", "prazo": "Trimestre", "impacto": "Y"},
        ]
        tarefas = build_default_tarefas(urgentes)

        assert len(tarefas) == 2
        assert tarefas[0]["n"] == 1
        assert tarefas[0]["t"] == "Reforçar reserva"
        assert tarefas[0]["p"] == "alta"  # lowercased
        assert tarefas[1]["e"] == "Trimestre"

    def test_default_tarefas_status(self):
        urgentes = [{"acao": "a"}, {"acao": "b"}, {"acao": "c"}]
        status = build_default_tarefas_status(urgentes)

        assert status == {"1": "pendente", "2": "pendente", "3": "pendente"}

    def test_empty_pontos_urgentes(self):
        assert build_default_tarefas([]) == []
        assert build_default_tarefas_status([]) == {}

    def test_none_pontos_urgentes(self):
        assert build_default_tarefas(None) == []  # type: ignore[arg-type]


# =============================================================================
# Alertas
# =============================================================================


class TestAlertas:
    def test_alerta_score_circular_nao_emitido(self):
        """A28.l10: "Score financeiro: X/10" era circular (alerta que não alerta);
        lista vazia é empty state honesto."""
        alertas = build_alertas(
            score={"valor": 7.5, "classificacao": "Bom"},
            ratios={},
        )
        assert alertas == []

    def test_alerta_rentabilidade_quando_nd(self):
        alertas = build_alertas(
            score={"valor": 5, "classificacao": "Regular"},
            ratios={"rentabilidade_pct": "N/D"},
        )
        assert "Rentabilidade: N/D" in alertas

    def test_sem_alerta_rentabilidade_quando_tem_valor(self):
        alertas = build_alertas(
            score={"valor": 5, "classificacao": "Regular"},
            ratios={"rentabilidade_pct": "12%"},
        )
        assert not any("Rentabilidade" in a for a in alertas)

    def test_alerta_trs_suspeita_quando_status_suspeito(self):
        # A28.l2: guardrail nunca publica número aberrante silencioso.
        alertas = build_alertas(
            score={"valor": 5, "classificacao": "Regular"},
            ratios={
                "rentabilidade_pct": "22.63",
                "rentabilidade": {"status": "suspeito", "valor_pct": 22.63},
            },
        )
        assert any("22.63% a.a. acima do plausível" in a for a in alertas)
        assert any("revisar composição" in a for a in alertas)

    def test_sem_alerta_trs_quando_status_ok(self):
        alertas = build_alertas(
            score={"valor": 5, "classificacao": "Regular"},
            ratios={
                "rentabilidade_pct": "3.25",
                "rentabilidade": {"status": "ok", "valor_pct": 3.25},
            },
        )
        assert not any("plausível" in a for a in alertas)


# =============================================================================
# build_e5_output
# =============================================================================


class TestBuildOutput:
    def test_has_all_required_sections(self):
        out = build_e5_output(_inputs())

        # Campos obrigatórios do schema + legado.
        for field in (
            "periodo_dados",
            "data_analise",
            "patrimonio",
            "goals",
            "fluxo_caixa",
            "ratios",
            "score",
            "orcamento_prospectivo",
            "reserva_emergencia",
            "endividamento",
            "previdencia_pgbl",
            "pontos_fortes",
            "pontos_urgentes",
            "investimentos",
            "equilibrio_cerbasi",
            "tarefas",
            "tarefas_status",
            "alertas",
            "consumo_consciente",
            "diagnostico_comportamental",
            "cenarios_conjuge",
            "programa_milhas",
        ):
            assert field in out

    def test_fluxo_caixa_key_name(self):
        """Legado chama 'fluxo_caixa' o valor de `fluxo`."""
        inp = _inputs(fluxo={"receita_total": 999})
        out = build_e5_output(inp)
        assert out["fluxo_caixa"]["receita_total"] == 999

    def test_tarefas_from_parsed_preferido_a_fallback(self):
        inp = _inputs(tarefas=[{"n": 99, "t": "Custom"}])
        out = build_e5_output(inp)
        assert out["tarefas"] == [{"n": 99, "t": "Custom"}]

    def test_tarefas_fallback_quando_nao_parsed(self):
        out = build_e5_output(_inputs())
        assert len(out["tarefas"]) == 1
        assert out["tarefas"][0]["t"] == "Reforçar reserva"

    def test_cenarios_conjuge_usa_chave_universal_estavel(self):
        """ADR-166: chave do payload é literal `cenarios_conjuge`, fixa e não-configurável."""
        inp = _inputs(cenarios_conjuge={"cenarios": [1, 2, 3]})
        out = build_e5_output(inp)
        assert "cenarios_conjuge" in out
        assert out["cenarios_conjuge"] == {"cenarios": [1, 2, 3]}
        # Garantir que o campo configurável foi removido do dataclass.
        assert not hasattr(inp, "cenarios_conjuge_key")

    def test_protecao_patrimonial_incluida_quando_presente(self):
        """A28.l6 (ADR-240 D8): bloco protecao_patrimonial entra no payload E5."""
        inp = _inputs(protecao_patrimonial={"apolices_vigentes": [], "gap_qualitativo": []})
        out = build_e5_output(inp)
        assert out["protecao_patrimonial"] == {"apolices_vigentes": [], "gap_qualitativo": []}

    def test_protecao_patrimonial_omitida_em_caller_legado(self):
        out = build_e5_output(_inputs())
        assert "protecao_patrimonial" not in out

    def test_narrativas_preservada_quando_existing(self):
        inp = _inputs(existing_narrativas={"resumo": "texto antigo"})
        out = build_e5_output(inp)
        assert out["narrativas"] == {"resumo": "texto antigo"}

    def test_narrativas_ausente_quando_primeiro_run(self):
        out = build_e5_output(_inputs())
        assert "narrativas" not in out

    def test_programa_milhas_default_dict_vazio(self):
        inp = _inputs(programa_milhas=None)
        out = build_e5_output(inp)
        assert out["programa_milhas"] == {}

    def test_alertas_sem_score_circular_e_com_nd(self):
        out = build_e5_output(_inputs())
        assert not any("Score financeiro" in a for a in out["alertas"])  # A28.l10
        assert any("N/D" in a for a in out["alertas"])


# =============================================================================
# proventos_por_ativo (A17 L4)
# =============================================================================


def _itsa4_summary():
    from decimal import Decimal

    from pipeline.domain.services.fiscal_source import InformeProventosSummary

    return InformeProventosSummary(
        ticker="ITSA4",
        ano_base=2024,
        total_proventos_brl=Decimal("60.00"),
        ir_retido_brl=Decimal("0"),
        custo_total_brl=Decimal("1000.00"),
        yield_on_cost_pct=Decimal("6.00"),
    )


def _informe_proventos_wege3() -> dict:
    evento = {
        "ticker": "WEGE3",
        "cnpj_pagador": "02332886000104",
        "tipo": "dividendo",
        "valor_brl": "100.00",
        "data_pagamento": "2024-06-15",
        "ir_retido_brl": "0",
    }
    payload = {
        "cnpj_emissor": "02332886000104",
        "nome_emissor": "XP",
        "proventos": [evento],
        "posicao_31_12": [],
    }
    return {"tipo_informe": "proventos_acoes", "ano_base": 2024, "proventos": payload}


class TestProventosPorAtivo:
    def test_output_emite_proventos_por_ativo_como_float(self):
        output = build_e5_output(_inputs(proventos_por_ativo=(_itsa4_summary(),)))
        (row,) = output["proventos_por_ativo"]
        assert row == {
            "ticker": "ITSA4",
            "ano_base": 2024,
            "total_proventos_brl": 60.0,
            "ir_retido_brl": 0.0,
            "custo_total_brl": 1000.0,
            "yield_on_cost_pct": 6.0,
        }

    def test_output_omite_chave_sem_informes(self):
        output = build_e5_output(_inputs())
        assert "proventos_por_ativo" not in output

    def test_loader_le_informes_do_store(self):
        from pipeline.artifact_store import InMemoryArtifactStore
        from pipeline.domain.services.e5_analyzer_adapter import (
            _try_load_proventos_summaries,
        )

        store = InMemoryArtifactStore().seed(
            "extract_informes_anuais", "informe_xp_2024", _informe_proventos_wege3()
        )
        (summary,) = _try_load_proventos_summaries(store)
        assert summary.ticker == "WEGE3"

    def test_loader_none_sem_informes(self):
        from pipeline.artifact_store import InMemoryArtifactStore
        from pipeline.domain.services.e5_analyzer_adapter import (
            _try_load_proventos_summaries,
        )

        assert _try_load_proventos_summaries(InMemoryArtifactStore()) is None
