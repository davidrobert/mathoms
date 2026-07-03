"""Tests — ``EquilibrioCerbasiAnalyzer`` (Sessão A5c)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.equilibrio_cerbasi_analyzer import (  # noqa: E402
    ClassificacaoFaixa,
    EquilibrioCerbasi,
    EquilibrioCerbasiAnalyzer,
    EquilibrioCerbasiConfig,
)


def _fluxo(despesas_por_categoria: dict) -> dict:
    return {"despesas_por_categoria": despesas_por_categoria}


class TestClassificacao:
    def test_investidor_quando_futuro_acima_30(self):
        # 40% futuro / 60% presente
        r = EquilibrioCerbasiAnalyzer().analyze(
            _fluxo(
                {
                    "moradia": 60_000,
                    "investimentos": 40_000,
                }
            )
        )
        assert r.pct_futuro == 40.0
        assert r.classificacao == "Investidor"

    def test_equilibrado_entre_20_e_30(self):
        r = EquilibrioCerbasiAnalyzer().analyze(
            _fluxo(
                {
                    "moradia": 75_000,
                    "investimentos": 25_000,
                }
            )
        )
        assert r.classificacao == "Equilibrado"

    def test_endividado_consciente_entre_10_e_20(self):
        r = EquilibrioCerbasiAnalyzer().analyze(
            _fluxo(
                {
                    "moradia": 85_000,
                    "investimentos": 15_000,
                }
            )
        )
        assert r.classificacao == "Endividado consciente"

    def test_gastador_abaixo_10(self):
        r = EquilibrioCerbasiAnalyzer().analyze(
            _fluxo(
                {
                    "moradia": 95_000,
                    "investimentos": 5_000,
                }
            )
        )
        assert r.classificacao == "Gastador"


class TestCategorias:
    def test_nao_classificado_entra_em_presente(self):
        r = EquilibrioCerbasiAnalyzer().analyze(
            _fluxo(
                {
                    "categoria_desconhecida": 50_000,
                    "investimentos": 50_000,
                }
            )
        )
        # 50 futuro / 50 presente → pct_futuro = 50, pct_presente = 50
        assert r.pct_futuro == 50.0
        assert r.pct_presente == 50.0

    def test_categorias_presente_default(self):
        r = EquilibrioCerbasiAnalyzer().analyze(
            _fluxo(
                {
                    "alimentacao": 50_000,  # presente
                    "transporte": 20_000,  # presente
                    "investimentos": 30_000,
                }
            )
        )
        assert r.pct_futuro == 30.0
        assert r.pct_presente == 70.0

    def test_categorias_futuro_default(self):
        r = EquilibrioCerbasiAnalyzer().analyze(
            _fluxo(
                {
                    "aportes": 40_000,  # futuro
                    "previdencia": 10_000,  # futuro
                    "moradia": 50_000,
                }
            )
        )
        assert r.pct_futuro == 50.0


class TestTotalZero:
    def test_zero_pct_quando_sem_despesas(self):
        r = EquilibrioCerbasiAnalyzer().analyze(_fluxo({}))
        assert r.pct_presente == 0.0
        assert r.pct_futuro == 0.0
        assert r.classificacao == "Gastador"


class TestConfig:
    def test_from_scoring_overrides_categorias(self):
        cfg = EquilibrioCerbasiConfig.from_scoring(
            {
                "cerbasi": {
                    "categorias_presente": ["casa"],
                    "categorias_futuro": ["invest"],
                }
            }
        )
        assert cfg.categorias_presente == frozenset({"casa"})
        assert cfg.categorias_futuro == frozenset({"invest"})

    def test_from_scoring_overrides_classificacao(self):
        cfg = EquilibrioCerbasiConfig.from_scoring(
            {
                "cerbasi": {
                    "classificacao": [
                        {"minimo_futuro_pct": 50, "label": "Super"},
                        {"minimo_futuro_pct": 0, "label": "Regular"},
                    ]
                }
            }
        )
        assert len(cfg.classificacao) == 2
        assert cfg.classificacao[0].label == "Super"

    def test_defaults_when_empty(self):
        cfg = EquilibrioCerbasiConfig.from_scoring({})
        assert "moradia" in cfg.categorias_presente
        assert "investimentos" in cfg.categorias_futuro


class TestResult:
    def test_is_frozen_dataclass(self):
        r = EquilibrioCerbasiAnalyzer().analyze(_fluxo({}))
        assert isinstance(r, EquilibrioCerbasi)

    def test_to_legacy_dict_has_required_fields(self):
        r = EquilibrioCerbasiAnalyzer().analyze(_fluxo({"moradia": 100}))
        d = r.to_legacy_dict()
        assert {"pct_presente", "pct_futuro", "classificacao", "presente", "futuro"}.issubset(
            d.keys()
        )
        assert d["presente"] == "Consolidação patrimonial"
        assert d["futuro"] == "Independência Financeira"


class TestJanelaCanonica:
    """ADR-306 §D5 — Cerbasi sobre renda da janela 12m; poupança conta como futuro."""

    @staticmethod
    def _fluxo_12m(
        despesas: dict, receita_recorrente: float, despesa_janela: float, n_meses: int = 12
    ) -> dict:
        return {
            "despesas_por_categoria": {"moradia": 999_999},  # full-period NÃO deve ser usado
            "janela_12m": {
                "despesas_por_categoria": despesas,
                "receita_recorrente": receita_recorrente,
                "despesa_total": despesa_janela,
                "n_meses": n_meses,
            },
        }

    def test_poupanca_28pct_nao_classifica_gastador(self):
        # Regressão dogfood 72883bde: 28% de poupança rotulado "Gastador".
        r = EquilibrioCerbasiAnalyzer().analyze(
            self._fluxo_12m({"moradia": 72_000}, receita_recorrente=100_000, despesa_janela=72_000)
        )
        assert r.pct_futuro == 28.0
        assert r.pct_presente == 72.0
        assert r.classificacao == "Equilibrado"
        assert r.janela == "12m"
        assert r.janela_meses == 12
        assert r.componentes["poupanca"] == 28_000.0

    def test_gasto_futuro_soma_com_poupanca(self):
        # 20k aportes (despesa futuro) + 15k poupança sobre renda 100k → 35% futuro.
        r = EquilibrioCerbasiAnalyzer().analyze(
            self._fluxo_12m(
                {"moradia": 65_000, "aportes": 20_000},
                receita_recorrente=100_000,
                despesa_janela=85_000,
            )
        )
        assert r.pct_futuro == 35.0
        assert r.classificacao == "Investidor"

    def test_deficit_sem_poupanca_pcts_somam_100(self):
        r = EquilibrioCerbasiAnalyzer().analyze(
            self._fluxo_12m(
                {"moradia": 120_000}, receita_recorrente=100_000, despesa_janela=120_000
            )
        )
        assert r.componentes["poupanca"] == 0.0
        assert r.pct_presente + r.pct_futuro == 100.0
        assert r.classificacao == "Gastador"

    def test_fallback_full_period_sem_janela(self):
        r = EquilibrioCerbasiAnalyzer().analyze(_fluxo({"moradia": 100}))
        assert r.janela == "full"

    def test_legacy_dict_carrega_rotulo_e_componentes(self):
        d = (
            EquilibrioCerbasiAnalyzer()
            .analyze(self._fluxo_12m({"moradia": 50}, receita_recorrente=100, despesa_janela=50))
            .to_legacy_dict()
        )
        assert {"janela", "janela_meses", "componentes"}.issubset(d.keys())
        assert d["componentes"]["base"] == 100.0


class TestCustomClassificacao:
    def test_custom_faixas_selecionam_corretamente(self):
        cfg = EquilibrioCerbasiConfig(
            classificacao=(
                ClassificacaoFaixa(80, "Top"),
                ClassificacaoFaixa(50, "Mid"),
                ClassificacaoFaixa(0, "Low"),
            )
        )
        # pct_futuro = 60 → Mid
        r = EquilibrioCerbasiAnalyzer(cfg).analyze(
            _fluxo(
                {
                    "moradia": 40_000,
                    "investimentos": 60_000,
                }
            )
        )
        assert r.classificacao == "Mid"
