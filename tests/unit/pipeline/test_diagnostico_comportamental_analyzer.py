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


def _fluxo_despesas(nao_id: float, outras: float) -> dict:
    return {
        "janela_12m": {"despesas_por_categoria": {"nao_identificado": nao_id, "outras": outras}}
    }


class TestConfianca:
    """RV2-21 / ADR-353 — degradê por cobertura de categorização."""

    def test_parcial_adiciona_ponto_cego_e_preserva_comportamental(self):
        an = DiagnosticoComportamentalAnalyzer()
        fluxo = _fluxo_despesas(21, 79)  # 21% → parcial
        padroes = {d.padrao for d in an.analyze(fluxo, _ratios(30))}
        assert "Disciplina de poupança" in padroes
        assert "Ponto cego nos gastos" in padroes
        assert an.confianca(fluxo)["nivel"] == "parcial"

    def test_insuficiente_suprime_comportamental(self):
        an = DiagnosticoComportamentalAnalyzer()
        fluxo = _fluxo_despesas(40, 60)  # 40% → insuficiente
        padroes = {d.padrao for d in an.analyze(fluxo, _ratios(30))}
        assert padroes == {"Diagnóstico indisponível — cobertura insuficiente"}
        assert an.confianca(fluxo)["nivel"] == "insuficiente"

    def test_alta_nao_altera_densidade(self):
        an = DiagnosticoComportamentalAnalyzer()
        fluxo = _fluxo_despesas(5, 95)  # 5% → alta
        padroes = {d.padrao for d in an.analyze(fluxo, _ratios(30))}
        assert "Ponto cego nos gastos" not in padroes
        assert an.confianca(fluxo)["nivel"] == "alta"

    def test_share_denominador_soma_categorias(self):
        an = DiagnosticoComportamentalAnalyzer()
        c = an.confianca(_fluxo_despesas(264, 736))  # 264/1000 = 26,4%
        assert c["nivel"] == "parcial"
        assert c["share_nao_identificado_pct"] == 26.4

    def test_sem_despesas_guard_alta(self):
        c = DiagnosticoComportamentalAnalyzer().confianca({"janela_12m": {}})
        assert c["nivel"] == "alta"
        assert c["share_nao_identificado_pct"] == 0.0
