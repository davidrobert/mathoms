"""Tests — ``BaselineNormalizer`` (Sessão A4a)."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.baseline_normalizer import (  # noqa: E402
    BaselineNormalizer,
    NormalizedBaseline,
)


_FIXED_DATE = date(2026, 4, 19)


def _normalizer() -> BaselineNormalizer:
    return BaselineNormalizer(date_today=_FIXED_DATE)


class TestPipelineStage:
    def test_adds_pipeline_stage_when_missing(self):
        out = _normalizer().normalize({"something": 1})
        assert out.data["pipeline_stage"] == "E1.5_Baseline_Patrimonial"
        assert "pipeline_stage added" in out.fixes

    def test_preserves_existing_pipeline_stage(self):
        out = _normalizer().normalize({"pipeline_stage": "E1.5"})
        assert out.data["pipeline_stage"] == "E1.5"
        assert "pipeline_stage added" not in out.fixes


class TestDataProcessamento:
    def test_derives_from_data_consolidacao(self):
        out = _normalizer().normalize({"data_consolidacao": "2025-06-01T12:00:00"})
        assert out.data["data_processamento"] == "2025-06-01"
        assert "data_processamento ← data_consolidacao" in out.fixes

    def test_defaults_to_today_when_missing(self):
        out = _normalizer().normalize({})
        assert out.data["data_processamento"] == "2026-04-19"
        assert "data_processamento set to today" in out.fixes

    def test_preserves_existing(self):
        out = _normalizer().normalize({"data_processamento": "2025-01-01"})
        assert out.data["data_processamento"] == "2025-01-01"


class TestMembros:
    def test_alias_from_membros_familia_extracts_names(self):
        out = _normalizer().normalize({
            "membros_familia": [
                {"nome": "David", "cpf": "123"},
                {"nome": "Mariana", "cpf": "456"},
            ]
        })
        assert out.data["membros"] == ["David", "Mariana"]

    def test_preserves_existing_membros(self):
        out = _normalizer().normalize({
            "membros": ["Existing"],
            "membros_familia": [{"nome": "Other"}],
        })
        assert out.data["membros"] == ["Existing"]


class TestPatrimonioPorAno:
    def test_builds_from_resumo_patrimonial(self):
        out = _normalizer().normalize({
            "resumo_patrimonial": {
                "31_12_2024": {"total": 1_000_000, "dividas": 100_000},
                "31_12_2023": {"bens_imoveis": 800_000, "dividas": 50_000},
            }
        })
        pat = out.data["patrimonio_por_ano"]
        assert pat["2024"] == {"total_bens": 1_000_000, "total_dividas": 100_000}
        assert pat["2023"] == {"total_bens": 800_000, "total_dividas": 50_000}

    def test_skips_non_matching_keys(self):
        out = _normalizer().normalize({
            "resumo_patrimonial": {
                "random_key": {"total": 100},
            }
        })
        assert "patrimonio_por_ano" not in out.data

    def test_preserves_existing(self):
        existing = {"2024": {"total_bens": 1, "total_dividas": 0}}
        out = _normalizer().normalize({
            "patrimonio_por_ano": existing,
            "resumo_patrimonial": {"31_12_2024": {"total": 999}},
        })
        assert out.data["patrimonio_por_ano"] == existing


class TestImoveisConsolidados:
    def test_alias_and_enriches_descricao_from_dados_completos(self):
        out = _normalizer().normalize({
            "bens_imoveis_consolidados": [
                {
                    "dados_completos": {"imovel": "Apto Vila Madalena"},
                    "valor": 500_000,
                }
            ]
        })
        imoveis = out.data["imoveis_consolidados"]
        assert imoveis[0]["descricao"] == "Apto Vila Madalena"

    def test_enriches_descricao_from_endereco(self):
        out = _normalizer().normalize({
            "bens_imoveis_consolidados": [{"endereco": "Rua X, 100"}]
        })
        assert out.data["imoveis_consolidados"][0]["descricao"] == "Rua X, 100"

    def test_adds_proprietario_from_proprietarios_list(self):
        out = _normalizer().normalize({
            "bens_imoveis_consolidados": [
                {"descricao": "Casa", "proprietarios": ["David", "Mariana"]}
            ]
        })
        assert out.data["imoveis_consolidados"][0]["proprietario"] == "David, Mariana"

    def test_preserves_existing_descricao(self):
        out = _normalizer().normalize({
            "bens_imoveis_consolidados": [
                {"descricao": "Já tinha", "endereco": "Rua Y"}
            ]
        })
        assert out.data["imoveis_consolidados"][0]["descricao"] == "Já tinha"


class TestInvestimentosConsolidados:
    def test_converts_dict_to_list(self):
        out = _normalizer().normalize({
            "investimentos_financeiros_consolidados": {
                "david_2024": {"tesouro": 100_000, "cdb": 50_000, "total": 150_000},
            }
        })
        inv = out.data["investimentos_consolidados"]
        assert len(inv) == 2  # total skipped
        nomes = sorted(i["tipo"] for i in inv)
        assert nomes == ["cdb", "tesouro"]
        # Proprietário derivado da chave.
        assert all(i["proprietario"] == "David" for i in inv)
        # Ano preservado em valores_31_12.
        assert inv[0]["valores_31_12"].get("2024") in (100_000, 50_000)

    def test_preserves_list_format(self):
        inv_list = [{"descricao": "Tesouro", "tipo": "tesouro", "proprietario": "David"}]
        out = _normalizer().normalize({
            "investimentos_financeiros_consolidados": inv_list
        })
        assert out.data["investimentos_consolidados"] == inv_list


class TestDividas:
    def test_alias_from_dividas_consolidados(self):
        out = _normalizer().normalize({"dividas_consolidados": [{"valor": 1000}]})
        assert out.data["dividas"] == [{"valor": 1000}]


class TestReturnType:
    def test_returns_normalized_baseline_dataclass(self):
        out = _normalizer().normalize({})
        assert isinstance(out, NormalizedBaseline)
        assert out.was_normalized is True

    def test_does_not_mutate_input(self):
        raw = {"data_consolidacao": "2025-01-01"}
        _normalizer().normalize(raw)
        assert raw == {"data_consolidacao": "2025-01-01"}

    def test_none_input_returns_empty(self):
        out = _normalizer().normalize(None)
        assert out.data == {}
        assert out.was_normalized is False

    def test_already_canonical_has_no_fixes(self):
        out = _normalizer().normalize({
            "pipeline_stage": "E1.5",
            "data_processamento": "2025-01-01",
        })
        assert out.fixes == ()
        assert out.was_normalized is False
