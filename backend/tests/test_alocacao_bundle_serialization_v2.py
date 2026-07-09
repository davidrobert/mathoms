"""Serializer do bundle emite v2 + rollup + E5 injeta derived (A12.alocacao-v2 PR6, ADR-141 §Emenda)."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from backend.app.services.pipeline.pipeline_adapter import _serialize_alocacao_goal
from pipeline.domain.services.e5_serialization import _enrich_alocacao_with_deviation

V2_INPUTS = {
    "rf_pos_pct": 20,
    "rf_pre_pct": 10,
    "rf_ipca_pct": 10,
    "acoes_br_pct": 25,
    "acoes_int_pct": 15,
    "fiis_pct": 10,
    "caixa_pct": 10,
    "rebalanceamento_modo": "por_aporte",
    "instrumentos": {"renda_fixa": "Tesouro Selic", "renda_variavel": "BOVA11"},
}
V1_INPUTS = {
    "renda_fixa_pct": 40,
    "acoes_pct": 30,
    "imoveis_reits_pct": 20,
    "liquidez_usd_pct": 10,
}
ORPHAN_INPUTS = {"rf_pct": 40, "rv_pct": 40, "alternativos_pct": 20}


def _goal(inputs: dict) -> SimpleNamespace:
    return SimpleNamespace(
        params_json={"inputs": inputs, "meta_version": 2},
        effective_from=date(2026, 1, 1),
    )


class TestSerializerV2:
    def test_emite_7_classes_e_rollup(self):
        out = _serialize_alocacao_goal(_goal(V2_INPUTS))
        assert out["rf_pos_pct"] == 20
        assert out["caixa_pct"] == 10
        assert out["rebalanceamento_modo"] == "por_aporte"
        # rollup 4-bucket p/ narrativa legada
        assert out["renda_fixa_pct"] == 40  # 20+10+10
        assert out["acoes_pct"] == 40  # 25+15
        assert out["imoveis_reits_pct"] == 10  # fiis
        assert out["liquidez_usd_pct"] == 10  # caixa
        assert out["instrumentos_rf"] == "Tesouro Selic"
        assert out["converted_from"] is None

    def test_row_v1_converte_on_read(self):
        out = _serialize_alocacao_goal(_goal(V1_INPUTS))
        assert out["converted_from"] == "1"
        assert out["rf_pos_pct"] == 20  # 40 → 50/25/25
        assert out["renda_fixa_pct"] == 40  # rollup preserva o total

    def test_row_orfa_converte(self):
        out = _serialize_alocacao_goal(_goal(ORPHAN_INPUTS))
        assert out["converted_from"] == "orphan"
        assert out["acoes_br_pct"] == 28

    def test_shape_irrecuperavel_degrada_sem_alvo(self):
        out = _serialize_alocacao_goal(_goal({"lixo": 1}))
        assert out == {"_source": "db:goals"}
        assert "rf_pos_pct" not in out


class TestE5InjectaDerived:
    def _goals_com_alvo(self):
        return {"alocacao_alvo": _serialize_alocacao_goal(_goal(V2_INPUTS))}

    def _tabela(self):
        return [
            {"categoria": "Renda Fixa", "valor": 500.0, "pct": 50.0},
            {"categoria": "Ações BR", "valor": 300.0, "pct": 30.0},
            {"categoria": "FIIs", "valor": 200.0, "pct": 20.0},
        ]

    def test_injeta_bloco_derived(self):
        enriched = _enrich_alocacao_with_deviation(self._goals_com_alvo(), self._tabela())
        derived = enriched["alocacao_alvo"]["derived"]
        assert "comparaveis" in derived
        assert "desvio_max_pct" in derived
        assert derived["rf_comparacao"] == "agregada"
        # não sobrescreve os inputs
        assert enriched["alocacao_alvo"]["rf_pos_pct"] == 20

    def test_sem_alvo_nao_injeta(self):
        goals = {"independencia_financeira": {"if_meta": 1000}}
        assert _enrich_alocacao_with_deviation(goals, self._tabela()) == goals

    def test_alvo_sem_tabela_nao_quebra(self):
        enriched = _enrich_alocacao_with_deviation(self._goals_com_alvo(), [])
        assert "derived" in enriched["alocacao_alvo"]
