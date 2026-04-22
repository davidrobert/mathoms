"""Tests — ``PontosUrgentesAnalyzer`` (Sessão A5c)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.pontos_urgentes_analyzer import (  # noqa: E402
    PontosUrgentesAnalyzer,
    PontosUrgentesConfig,
    PontoUrgenteItem,
)


def _ratios(endiv: float = 10.0, rent: str = "15%") -> dict:
    return {"taxa_endividamento_pct": endiv, "rentabilidade_pct": rent}


def _reserva(cobertura: float = 12.0) -> dict:
    return {"cobertura_meses": cobertura}


def _pat() -> dict:
    return {"bruto": 1_000_000, "dividas": 0}


class TestReserva:
    def test_dispara_quando_abaixo_do_minimo(self):
        out = PontosUrgentesAnalyzer().analyze(_ratios(), _reserva(cobertura=3), _pat())
        acoes = {i.acao for i in out}
        assert "Reforçar reserva de emergência" in acoes

    def test_nao_dispara_quando_adequada(self):
        out = PontosUrgentesAnalyzer().analyze(_ratios(), _reserva(cobertura=12), _pat())
        acoes = {i.acao for i in out}
        assert "Reforçar reserva de emergência" not in acoes


class TestEndividamento:
    def test_dispara_quando_acima_do_maximo(self):
        out = PontosUrgentesAnalyzer().analyze(_ratios(endiv=25), _reserva(), _pat())
        acoes = {i.acao for i in out}
        assert "Reduzir endividamento" in acoes

    def test_nao_dispara_quando_ok(self):
        out = PontosUrgentesAnalyzer().analyze(_ratios(endiv=10), _reserva(), _pat())
        acoes = {i.acao for i in out}
        assert "Reduzir endividamento" not in acoes


class TestSeguro:
    def test_sempre_adicionado(self):
        out = PontosUrgentesAnalyzer().analyze(_ratios(), _reserva(), _pat())
        acoes = {i.acao for i in out}
        assert "Contratar seguro de vida e invalidez" in acoes


class TestRentabilidade:
    def test_dispara_quando_nd(self):
        out = PontosUrgentesAnalyzer().analyze(_ratios(rent="N/D"), _reserva(), _pat())
        acoes = {i.acao for i in out}
        assert "Consolidar dados de rentabilidade dos investimentos" in acoes

    def test_nao_dispara_quando_tem_valor(self):
        out = PontosUrgentesAnalyzer().analyze(_ratios(rent="12.5"), _reserva(), _pat())
        acoes = {i.acao for i in out}
        assert "Consolidar dados de rentabilidade dos investimentos" not in acoes


class TestConfig:
    def test_from_scoring(self):
        cfg = PontosUrgentesConfig.from_scoring(
            {
                "thresholds_alertas": {
                    "reserva_minima_meses": 12,
                    "endividamento_maximo_pct": 10,
                }
            }
        )
        assert cfg.reserva_minima_meses == 12.0
        assert cfg.endividamento_maximo_pct == 10.0


class TestResult:
    def test_item_to_dict(self):
        item = PontoUrgenteItem("Alta", "Ação X", "Impacto", "Imediato")
        d = item.to_dict()
        assert d == {
            "prioridade": "Alta",
            "acao": "Ação X",
            "impacto": "Impacto",
            "prazo": "Imediato",
        }

    def test_seguro_sempre_presente_mesmo_quando_tudo_ok(self):
        out = PontosUrgentesAnalyzer().analyze(
            _ratios(endiv=5, rent="10%"), _reserva(cobertura=24), _pat()
        )
        # Sem reserva, sem endividamento, sem rentabilidade N/D.
        # Seguro é o único que dispara.
        assert len(out) == 1
        assert out[0].acao == "Contratar seguro de vida e invalidez"
