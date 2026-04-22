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
