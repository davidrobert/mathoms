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
    def test_gera_quando_excelente(self):
        out = PontosFortesAnalyzer().analyze(
            **_args(score={"classificacao": "Excelente", "valor": 8.5})
        )
        titulos = {p.titulo for p in out}
        assert "Score Financeiro Positivo" in titulos

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


class TestDiversificacao:
    def test_gera_com_4_categorias_ou_mais(self):
        categorias = [
            {"valor": 100}, {"valor": 50}, {"valor": 25}, {"valor": 10},
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


class TestColchaoPatrimonial:
    def test_robusto_acima_24(self):
        out = PontosFortesAnalyzer().analyze(
            **_args(ratios={"cobertura_despesas_meses": 30, "taxa_endividamento_pct": 50})
        )
        titulos = {p.titulo for p in out}
        assert "Colchão Patrimonial Robusto" in titulos

    def test_solido_12_a_24(self):
        out = PontosFortesAnalyzer().analyze(
            **_args(ratios={"cobertura_despesas_meses": 18, "taxa_endividamento_pct": 50})
        )
        titulos = {p.titulo for p in out}
        assert "Patrimônio Investível Sólido" in titulos


class TestProgressoIF:
    def test_gera_acima_de_20pct(self):
        out = PontosFortesAnalyzer().analyze(**_args(goals={"progresso_pct": 25}))
        titulos = {p.titulo for p in out}
        assert "Caminho para Independência Financeira" in titulos


class TestPatrimonio1M:
    def test_gera_quando_bruto_acima_1M(self):
        out = PontosFortesAnalyzer().analyze(**_args(patrimonio={"bruto": 1_500_000, "categorias": []}))
        titulos = {p.titulo for p in out}
        assert "Patrimônio Acima de R$ 1M" in titulos


class TestFallback:
    def test_fallback_quando_tudo_zero(self):
        out = PontosFortesAnalyzer().analyze(**_args(
            ratios={"taxa_poupanca_recorrente_pct": 0, "taxa_endividamento_pct": 50, "cobertura_despesas_meses": 0},
        ))
        titulos = {p.titulo for p in out}
        assert "Análise em Andamento" in titulos


class TestConfig:
    def test_from_scoring(self):
        cfg = PontosFortesConfig.from_scoring({
            "thresholds_alertas": {
                "pontos_fortes_taxa_poupanca_min_pct": 40,
                "endividamento_maximo_pct": 15,
            }
        })
        assert cfg.poupanca_forte_min_pct == 40.0
        assert cfg.endividamento_max_pct == 15.0


class TestResult:
    def test_item_to_dict(self):
        item = PontoForteItem("T", "D", "icon")
        assert item.to_dict() == {"titulo": "T", "descricao": "D", "icone": "icon"}
