"""Tests — ``PontosFortesAnalyzer`` (Sessão A5c)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.pontos_fortes_analyzer import (  # noqa: E402
    PontoForteItem,
    PontosFortesAnalyzer,
    PontosFortesConfig,
)


def _args(**overrides):
    defaults = {
        "score": {"classificacao": "", "valor": 5.0},
        "ratios": {
            "taxa_poupanca_recorrente_pct": 0,
            "taxa_endividamento_pct": 50,
            "cobertura_despesas_meses": 0,
        },
        "patrimonio": {"bruto": 0, "categorias": []},
        "fluxo": {},
        "reserva": {"cobertura_meses": 0},
        "goals": {"progresso_pct": 0},
    }
    defaults.update(overrides)
    return defaults


class TestScoreFinanceiro:
    def test_nao_gera_mesmo_quando_excelente(self):
        """A28.l10: ponto de score é circular (referencia só o próprio score) — suprimido."""
        out = PontosFortesAnalyzer().analyze(
            **_args(score={"classificacao": "Excelente", "valor": 8.5})
        )
        titulos = {p.titulo for p in out}
        assert "Score Financeiro Positivo" not in titulos

    def test_nao_gera_quando_regular(self):
        out = PontosFortesAnalyzer().analyze(
            **_args(score={"classificacao": "Regular", "valor": 5.0})
        )
        titulos = {p.titulo for p in out}
        assert "Score Financeiro Positivo" not in titulos


class TestPoupanca:
    def test_elevada_acima_do_minimo(self):
        out = PontosFortesAnalyzer().analyze(
            **_args(ratios={"taxa_poupanca_recorrente_pct": 40, "taxa_endividamento_pct": 5})
        )
        titulos = {p.titulo for p in out}
        assert "Taxa de Poupança Elevada" in titulos

    def test_disciplina_entre_15_e_minimo(self):
        out = PontosFortesAnalyzer().analyze(
            **_args(ratios={"taxa_poupanca_recorrente_pct": 20, "taxa_endividamento_pct": 5})
        )
        titulos = {p.titulo for p in out}
        assert "Disciplina de Poupança" in titulos
        assert "Taxa de Poupança Elevada" not in titulos

    def test_abaixo_de_15_nao_gera(self):
        out = PontosFortesAnalyzer().analyze(
            **_args(ratios={"taxa_poupanca_recorrente_pct": 10, "taxa_endividamento_pct": 5})
        )
        titulos = {p.titulo for p in out}
        assert "Taxa de Poupança Elevada" not in titulos
        assert "Disciplina de Poupança" not in titulos


class TestEndividamento:
    def test_minimo_quando_abaixo_de_5(self):
        out = PontosFortesAnalyzer().analyze(
            **_args(ratios={"taxa_endividamento_pct": 2, "taxa_poupanca_recorrente_pct": 0})
        )
        titulos = {p.titulo for p in out}
        assert "Endividamento Mínimo" in titulos

    def test_controlado_entre_5_e_max(self):
        out = PontosFortesAnalyzer().analyze(
            **_args(ratios={"taxa_endividamento_pct": 15, "taxa_poupanca_recorrente_pct": 0})
        )
        titulos = {p.titulo for p in out}
        assert "Endividamento Controlado" in titulos

    def test_acima_do_max_nao_gera(self):
        out = PontosFortesAnalyzer().analyze(
            **_args(ratios={"taxa_endividamento_pct": 30, "taxa_poupanca_recorrente_pct": 0})
        )
        titulos = {p.titulo for p in out}
        assert "Endividamento Mínimo" not in titulos
        assert "Endividamento Controlado" not in titulos


class TestReserva:
    def test_excelente_acima_12_meses(self):
        out = PontosFortesAnalyzer().analyze(**_args(reserva={"cobertura_meses": 18}))
        titulos = {p.titulo for p in out}
        assert "Reserva de Emergência Excelente" in titulos

    def test_adequada_6_a_12(self):
        out = PontosFortesAnalyzer().analyze(**_args(reserva={"cobertura_meses": 8}))
        titulos = {p.titulo for p in out}
        assert "Reserva de Emergência Adequada" in titulos

    def test_excelente_relativo_ao_alvo_do_perfil(self):
        """A28.l1: perfil PJ-dominante (alvo 18) com 13 meses NÃO é excelente."""
        out = PontosFortesAnalyzer().analyze(
            **_args(reserva={"cobertura_meses": 13, "meses_alvo": 18})
        )
        titulos = {p.titulo for p in out}
        assert "Reserva de Emergência Excelente" not in titulos
        assert "Reserva de Emergência Adequada" in titulos

    def test_excelente_quando_atinge_alvo_do_perfil(self):
        out = PontosFortesAnalyzer().analyze(
            **_args(reserva={"cobertura_meses": 19, "meses_alvo": 18})
        )
        item = next(p for p in out if p.titulo == "Reserva de Emergência Excelente")
        assert "18 meses" in item.descricao

    def test_robusta_quando_motor_marca_excessiva(self):
        """C5-C1: reserva 'Excessiva' vira 'Robusta' (excedente realocável), não 'Excelente'."""
        out = PontosFortesAnalyzer().analyze(
            **_args(
                reserva={
                    "cobertura_meses": 26,
                    "meses_alvo": 12,
                    "avaliacao_liquidity": "Excessiva",
                }
            )
        )
        titulos = {p.titulo for p in out}
        assert "Reserva de Emergência Robusta" in titulos
        assert "Reserva de Emergência Excelente" not in titulos
        item = next(p for p in out if p.titulo == "Reserva de Emergência Robusta")
        assert "excedente" in item.descricao.lower()

    def test_robusta_quando_2x_o_alvo_sem_flag(self):
        out = PontosFortesAnalyzer().analyze(
            **_args(reserva={"cobertura_meses": 25, "meses_alvo": 12})
        )
        titulos = {p.titulo for p in out}
        assert "Reserva de Emergência Robusta" in titulos
        assert "Reserva de Emergência Excelente" not in titulos


class TestDiversificacao:
    def test_gera_com_4_categorias_ou_mais(self):
        categorias = [
            {"valor": 100},
            {"valor": 50},
            {"valor": 25},
            {"valor": 10},
        ]
        out = PontosFortesAnalyzer().analyze(
            **_args(patrimonio={"bruto": 500, "categorias": categorias})
        )
        titulos = {p.titulo for p in out}
        assert "Patrimônio Diversificado" in titulos

    def test_nao_gera_com_menos_de_4(self):
        categorias = [{"valor": 100}, {"valor": 50}, {"valor": 25}]
        out = PontosFortesAnalyzer().analyze(
            **_args(patrimonio={"bruto": 175, "categorias": categorias})
        )
        titulos = {p.titulo for p in out}
        assert "Patrimônio Diversificado" not in titulos


class TestAutonomiaFinanceira:
    """ADR-335: ex-'Colchão Patrimonial'; lê `autonomia_financeira_meses`."""

    def test_ampla_acima_24(self):
        out = PontosFortesAnalyzer().analyze(
            **_args(ratios={"autonomia_financeira_meses": 30, "taxa_endividamento_pct": 50})
        )
        titulos = {p.titulo for p in out}
        assert "Autonomia Financeira Ampla" in titulos

    def test_solida_12_a_24(self):
        out = PontosFortesAnalyzer().analyze(
            **_args(ratios={"autonomia_financeira_meses": 18, "taxa_endividamento_pct": 50})
        )
        titulos = {p.titulo for p in out}
        assert "Autonomia Financeira Sólida" in titulos

    def test_le_alias_deprecated_cobertura(self):
        # Consumidor antigo que só emite `cobertura_despesas_meses` ainda funciona (1 ciclo).
        out = PontosFortesAnalyzer().analyze(
            **_args(
                reserva={"cobertura_meses": 4},
                ratios={"cobertura_despesas_meses": 30, "taxa_endividamento_pct": 50},
            )
        )
        titulos = {p.titulo for p in out}
        assert "Autonomia Financeira Ampla" in titulos

    def test_suprimido_quando_reserva_ja_gerou_ponto(self):
        """A28.l10: reserva e autonomia são a mesma família de cobertura em meses —
        emitir os dois é redundante; reserva vence."""
        out = PontosFortesAnalyzer().analyze(
            **_args(
                reserva={"cobertura_meses": 18},
                ratios={"autonomia_financeira_meses": 30, "taxa_endividamento_pct": 50},
            )
        )
        titulos = {p.titulo for p in out}
        assert "Reserva de Emergência Excelente" in titulos
        assert "Autonomia Financeira Ampla" not in titulos
        assert "Autonomia Financeira Sólida" not in titulos

    def test_emitido_quando_reserva_abaixo_de_6_meses(self):
        out = PontosFortesAnalyzer().analyze(
            **_args(
                reserva={"cobertura_meses": 4},
                ratios={"autonomia_financeira_meses": 30, "taxa_endividamento_pct": 50},
            )
        )
        titulos = {p.titulo for p in out}
        assert "Autonomia Financeira Ampla" in titulos


class TestProgressoIF:
    def test_gera_acima_de_20pct(self):
        out = PontosFortesAnalyzer().analyze(**_args(goals={"progresso_pct": 25}))
        titulos = {p.titulo for p in out}
        assert "Caminho para Independência Financeira" in titulos


class TestPatrimonio1M:
    def test_gera_quando_bruto_acima_1M(self):
        out = PontosFortesAnalyzer().analyze(
            **_args(patrimonio={"bruto": 1_500_000, "categorias": []})
        )
        titulos = {p.titulo for p in out}
        assert "Patrimônio Acima de R$ 1M" in titulos


class TestFallback:
    def test_fallback_quando_tudo_zero(self):
        out = PontosFortesAnalyzer().analyze(
            **_args(
                ratios={
                    "taxa_poupanca_recorrente_pct": 0,
                    "taxa_endividamento_pct": 50,
                    "cobertura_despesas_meses": 0,
                },
            )
        )
        titulos = {p.titulo for p in out}
        assert "Análise em Andamento" in titulos


class TestConfig:
    def test_from_scoring(self):
        cfg = PontosFortesConfig.from_scoring(
            {
                "thresholds_alertas": {
                    "pontos_fortes_taxa_poupanca_min_pct": 40,
                    "endividamento_maximo_pct": 15,
                }
            }
        )
        assert cfg.poupanca_forte_min_pct == 40.0
        assert cfg.endividamento_max_pct == 15.0


class TestResult:
    def test_item_to_dict(self):
        item = PontoForteItem("T", "D", "icon")
        assert item.to_dict() == {"titulo": "T", "descricao": "D", "icone": "icon"}


# ---------------------------------------------------------------------------
# A prosa do exec context não afirma limiar que o catálogo se recusa a arbitrar
# (A40.l90 · [[ADR-419]])
# ---------------------------------------------------------------------------


_SCORING_PROSA = {
    "thresholds_alertas": {
        "pontos_fortes_taxa_poupanca_min_pct": 30,
        "poupanca_referencia_pct": 25,
        "endividamento_maximo_pct": 20,
    }
}


def _descricao(titulo: str, ratios: dict) -> str:
    from pipeline.domain.services.pontos_fortes_analyzer import (
        PontosFortesAnalyzer,
        PontosFortesConfig,
    )

    itens = PontosFortesAnalyzer(PontosFortesConfig.from_scoring(_SCORING_PROSA)).analyze(
        score={}, ratios=ratios, patrimonio={}, fluxo={}, reserva={}, goals={}
    )
    return next(i.descricao for i in itens if i.titulo == titulo)


def test_prosa_de_poupanca_nao_afirma_o_limiar_orfao():
    """`taxa_poupanca_recorrente` é órfã por decisão — 25 e 30 rivalizam (RV2-24)."""
    # Esta linha vai ao exec context como afirmação da própria E5; citar "referência de
    # 30%" entregava ao modelo um limiar que o produtor canônico se recusa a publicar.
    desc = _descricao("Taxa de Poupança Elevada", {"taxa_poupanca_recorrente_pct": 42.0})
    assert "30" not in desc and "25" not in desc, desc
    assert "referência" not in desc.lower()
    assert "42" in desc  # o observado permanece


def test_prosa_de_endividamento_pode_citar_o_teto_porque_e_a_mesma_chave():
    """Contraste deliberado com o teste acima: aqui o número TEM fonte única."""
    desc = _descricao("Endividamento Controlado", {"taxa_endividamento_pct": 8.0})
    assert "20" in desc


def test_teto_de_endividamento_da_prosa_e_o_mesmo_limiar_do_catalogo():
    """Gate de neutralidade: se as fontes divergirem, a prosa vira afirmação órfã."""
    # Sem ele, a neutralidade medida hoje — prosa e catálogo lendo
    # `thresholds_alertas.endividamento_maximo_pct` — se desfaz em silêncio.
    from pipeline.domain.services.kpi_target_catalog import build_kpi_targets
    from pipeline.domain.services.pontos_fortes_analyzer import PontosFortesConfig

    alvo = build_kpi_targets({"ratios": {}}, scoring=_SCORING_PROSA)["taxa_endividamento"]
    assert alvo["limiar"] == PontosFortesConfig.from_scoring(_SCORING_PROSA).endividamento_max_pct
