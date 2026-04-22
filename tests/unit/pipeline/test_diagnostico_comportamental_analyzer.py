"""Tests — ``DiagnosticoComportamentalAnalyzer`` (Sessão A5c)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.diagnostico_comportamental_analyzer import (  # noqa: E402
    DiagnosticoComportamentalAnalyzer,
    DiagnosticoComportamentalConfig,
    DiagnosticoItem,
)


def _fluxo(
    *,
    receita_total: float = 100_000,
    receita_one_time: float = 10_000,
    janela: bool = True,
) -> dict:
    if janela:
        return {
            "janela_12m": {
                "receita_total": receita_total,
                "receita_one_time": receita_one_time,
            }
        }
    return {
        "receita_total": receita_total,
        "receita_one_time": receita_one_time,
    }


def _ratios(taxa: float) -> dict:
    return {"taxa_poupanca_recorrente_pct": taxa}


class TestPoupanca:
    def test_alta_gera_disciplina(self):
        out = DiagnosticoComportamentalAnalyzer().analyze(_fluxo(), _ratios(30))
        padroes = {d.padrao for d in out}
        assert "Disciplina de poupança" in padroes

    def test_baixa_gera_alerta(self):
        out = DiagnosticoComportamentalAnalyzer().analyze(_fluxo(), _ratios(10))
        padroes = {d.padrao for d in out}
        assert "Poupança abaixo do ideal" in padroes

    def test_zero_nao_gera(self):
        out = DiagnosticoComportamentalAnalyzer().analyze(_fluxo(), _ratios(0))
        padroes = {d.padrao for d in out}
        assert "Poupança abaixo do ideal" not in padroes
        assert "Disciplina de poupança" not in padroes


class TestReceitaOneTime:
    def test_dispara_quando_acima_do_alerta(self):
        out = DiagnosticoComportamentalAnalyzer().analyze(
            _fluxo(receita_total=100_000, receita_one_time=40_000),
            _ratios(30),
        )
        padroes = {d.padrao for d in out}
        assert "Alta dependência de receita pontual" in padroes

    def test_nao_dispara_quando_abaixo(self):
        out = DiagnosticoComportamentalAnalyzer().analyze(
            _fluxo(receita_total=100_000, receita_one_time=10_000),
            _ratios(30),
        )
        padroes = {d.padrao for d in out}
        assert "Alta dependência de receita pontual" not in padroes

    def test_nao_dispara_com_receita_zero(self):
        out = DiagnosticoComportamentalAnalyzer().analyze(
            _fluxo(receita_total=0, receita_one_time=0), _ratios(30)
        )
        padroes = {d.padrao for d in out}
        assert "Alta dependência de receita pontual" not in padroes


class TestFallback:
    def test_retorna_analise_em_andamento_quando_nada_dispara(self):
        out = DiagnosticoComportamentalAnalyzer().analyze(
            _fluxo(receita_total=0, receita_one_time=0), _ratios(0)
        )
        assert len(out) == 1
        assert out[0].padrao == "Análise em andamento"


class TestJanelaFallback:
    def test_usa_fluxo_quando_janela_ausente(self):
        out = DiagnosticoComportamentalAnalyzer().analyze(
            _fluxo(receita_total=100_000, receita_one_time=40_000, janela=False),
            _ratios(30),
        )
        padroes = {d.padrao for d in out}
        assert "Alta dependência de receita pontual" in padroes


class TestConfig:
    def test_from_scoring_overrides_defaults(self):
        cfg = DiagnosticoComportamentalConfig.from_scoring(
            {
                "thresholds_alertas": {
                    "poupanca_referencia_pct": 30,
                    "receita_one_time_alerta_pct": 50,
                }
            }
        )
        assert cfg.poupanca_ref_pct == 30.0
        assert cfg.receita_one_time_alerta_pct == 50.0

    def test_defaults_when_empty(self):
        cfg = DiagnosticoComportamentalConfig.from_scoring({})
        assert cfg.poupanca_ref_pct == 25.0


class TestResult:
    def test_retorna_list_of_diagnostico_item(self):
        out = DiagnosticoComportamentalAnalyzer().analyze(_fluxo(), _ratios(30))
        assert all(isinstance(d, DiagnosticoItem) for d in out)

    def test_to_dict_serialization(self):
        item = DiagnosticoItem("P", "E", "M")
        d = item.to_dict()
        assert d == {"padrao": "P", "evidencia": "E", "mudanca_sugerida": "M"}
