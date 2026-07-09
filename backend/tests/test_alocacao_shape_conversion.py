"""Conversão on-read v1/órfão → v2 de alocação-alvo (ADR-141 §Emenda 2026-07-08)."""

from __future__ import annotations

import pytest

from backend.app.schemas.dto.goal import ALOCACAO_V2_CLASS_FIELDS, AlocacaoGoalInputsV2
from backend.app.schemas.dto.goal.alocacao_shape_conversion import (
    compute_alocacao_derived_v2,
    convert_alocacao_inputs_to_v2,
    detect_alocacao_shape,
    map_rebalanceamento_legado,
)

V1_PADRAO = {
    "renda_fixa_pct": 40.0,
    "acoes_pct": 30.0,
    "imoveis_reits_pct": 20.0,
    "liquidez_usd_pct": 10.0,
    "instrumentos_rf": "Tesouro Selic",
    "instrumentos_rv": "BOVA11",
    "rebalanceamento": "anual",
}
ORPHAN_SEED_DEFAULT = {"rf_pct": 40, "rv_pct": 40, "alternativos_pct": 20}
ORPHAN_SEED_DEMO = {"rf_pct": 30, "rv_pct": 50, "alternativos_pct": 20}
V2_MINIMO = {campo: (100 if campo == "rf_pos_pct" else 0) for campo in ALOCACAO_V2_CLASS_FIELDS}


class TestDetectShape:
    def test_fingerprints(self):
        assert detect_alocacao_shape(V1_PADRAO) == "v1"
        assert detect_alocacao_shape(ORPHAN_SEED_DEFAULT) == "orphan"
        assert detect_alocacao_shape(V2_MINIMO) == "v2"
        assert detect_alocacao_shape({}) == "unknown"
        assert detect_alocacao_shape(None) == "unknown"

    def test_meta_version_nao_influencia(self):
        # rows do seed carimbam meta_version=1 num shape órfão — fingerprint decide.
        assert detect_alocacao_shape({**ORPHAN_SEED_DEFAULT, "meta_version": 1}) == "orphan"

    def test_v1_parcial_ainda_detecta_v1(self):
        assert detect_alocacao_shape({"renda_fixa_pct": 100}) == "v1"


class TestConversaoV1:
    def test_split_rf_50_25_25_e_usd_70_30(self):
        v2, origem = convert_alocacao_inputs_to_v2(V1_PADRAO)
        assert origem == "1"
        assert v2["rf_pos_pct"] == 20
        assert v2["rf_pre_pct"] == 10
        assert v2["rf_ipca_pct"] == 10
        assert v2["acoes_br_pct"] == 30
        assert v2["fiis_pct"] == 20
        assert v2["acoes_int_pct"] == 7
        assert v2["caixa_pct"] == 3

    def test_soma_100_inteira_e_valida_no_dto(self):
        v2, _ = convert_alocacao_inputs_to_v2(V1_PADRAO)
        soma = sum(v2[campo] for campo in ALOCACAO_V2_CLASS_FIELDS)
        assert soma == 100
        modelo = AlocacaoGoalInputsV2(**v2)
        assert compute_alocacao_derived_v2(modelo).soma_percentuais == 100

    def test_instrumentos_e_rebalanceamento_migram(self):
        v2, _ = convert_alocacao_inputs_to_v2(V1_PADRAO)
        assert v2["instrumentos"] == {"renda_fixa": "Tesouro Selic", "renda_variavel": "BOVA11"}
        assert v2["rebalanceamento_modo"] == "anual"

    def test_v1_soma_diferente_de_100_normaliza(self):
        v2, _ = convert_alocacao_inputs_to_v2({"renda_fixa_pct": 50, "acoes_pct": 25})
        assert sum(v2[campo] for campo in ALOCACAO_V2_CLASS_FIELDS) == 100


class TestConversaoOrfao:
    def test_seed_default_40_40_20(self):
        v2, origem = convert_alocacao_inputs_to_v2(ORPHAN_SEED_DEFAULT)
        assert origem == "orphan"
        assert v2["rf_pos_pct"] == 20
        assert v2["rf_pre_pct"] == 10
        assert v2["rf_ipca_pct"] == 10
        assert v2["acoes_br_pct"] == 28
        assert v2["acoes_int_pct"] == 12
        assert v2["fiis_pct"] == 20
        assert v2["caixa_pct"] == 0

    def test_seed_demo_30_50_20_residuo_em_rf_pos(self):
        # RF 30 → 15/7.5/7.5: floor + resíduo integral em rf_pos (16/7/7),
        # viés conservador aprovado pelo financial-planner (emenda item 5).
        v2, _ = convert_alocacao_inputs_to_v2(ORPHAN_SEED_DEMO)
        assert sum(v2[campo] for campo in ALOCACAO_V2_CLASS_FIELDS) == 100
        assert v2["rf_pos_pct"] == 16
        assert v2["rf_pre_pct"] == 7
        assert v2["rf_ipca_pct"] == 7
        AlocacaoGoalInputsV2(**v2)

    def test_orfao_sem_valores_degrada_para_none(self):
        v2, origem = convert_alocacao_inputs_to_v2(
            {"rf_pct": 0, "rv_pct": 0, "alternativos_pct": 0}
        )
        assert v2 is None
        assert origem is None


class TestPassthroughV2:
    def test_v2_intacto_sem_converted_from(self):
        v2, origem = convert_alocacao_inputs_to_v2(V2_MINIMO)
        assert origem is None
        assert v2 == V2_MINIMO

    def test_idempotencia(self):
        primeira, _ = convert_alocacao_inputs_to_v2(V1_PADRAO)
        segunda, origem = convert_alocacao_inputs_to_v2(primeira)
        assert segunda == primeira
        assert origem is None


class TestRebalanceamentoLegado:
    @pytest.mark.parametrize(
        ("legado", "esperado"),
        [
            ("anual", "anual"),
            ("Semestral", "semestral"),
            ("Quando desviar >5%", "trigger_5pct"),
            ("quando desviar >10%", "trigger_10pct"),
            ("no aporte", "por_aporte"),
            ("Trimestral", "trimestral"),
            ("", "por_aporte"),
            (None, "por_aporte"),
            ("qualquer coisa", "por_aporte"),
        ],
    )
    def test_mapping(self, legado, esperado):
        assert map_rebalanceamento_legado(legado) == esperado
