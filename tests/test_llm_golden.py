#!/usr/bin/env python3
"""Golden file / snapshot tests — validate that LLM output schemas parse
golden fixtures correctly and that validators accept them.

Fixture inventory: tests/fixtures/llm_golden/README.md
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

GOLDEN_DIR = Path(__file__).resolve().parent / "fixtures" / "llm_golden"


class TestE1GoldenFile:
    @pytest.fixture
    def golden_data(self):
        return json.loads((GOLDEN_DIR / "e1_members_output.json").read_text())

    def test_schema_parses(self, golden_data):
        from pipeline.llm.schemas.e1_members import MembersExtractOutput

        output = MembersExtractOutput(**golden_data)
        assert len(output.members) == 2
        assert output.titular_key == "david"
        assert output.confidence == 0.95

    def test_validator_accepts(self, golden_data):
        from pipeline.llm.schemas.e1_members import MembersExtractOutput
        from pipeline.llm.validators import validate_e1_output

        output = MembersExtractOutput(**golden_data)
        result = validate_e1_output(output)
        assert result.valid, f"Errors: {result.errors}"
        assert len(result.warnings) == 0

    def test_output_converter(self, golden_data):
        from pipeline.llm.schemas.e1_members import MembersExtractOutput
        from pipeline.stages.extract_members import _output_to_family_members_json

        output = MembersExtractOutput(**golden_data)
        fmj = _output_to_family_members_json(output)

        assert "david" in fmj["membros"]
        assert "mariana" in fmj["membros"]
        assert fmj["membros"]["david"]["cpf"] == "12345678901"
        assert fmj["banco_membro"]["itau"] == "david"
        assert fmj["banco_membro"]["c6bank"] == "david"
        assert fmj["banco_membro"]["nubank"] == "mariana"

    def test_member_keys_are_lowercase_no_spaces(self, golden_data):
        for m in golden_data["members"]:
            assert m["key"].islower()
            assert " " not in m["key"]


class TestE15GoldenFile:
    @pytest.fixture
    def golden_data(self):
        return json.loads((GOLDEN_DIR / "e15_baseline_output.json").read_text())

    def test_schema_parses(self, golden_data):
        from pipeline.llm.schemas.e15_baseline import BaselinePatrimonialOutput

        output = BaselinePatrimonialOutput(**golden_data)
        assert len(output.items) == 5
        assert output.net_worth_brl == 897000.00
        assert output.reference_year == 2024

    def test_validator_accepts(self, golden_data):
        from pipeline.llm.schemas.e15_baseline import BaselinePatrimonialOutput
        from pipeline.llm.validators import validate_e15_output

        output = BaselinePatrimonialOutput(**golden_data)
        result = validate_e15_output(output)
        assert result.valid, f"Errors: {result.errors}"

    def test_output_converter(self, golden_data):
        from pipeline.llm.schemas.e15_baseline import BaselinePatrimonialOutput
        from pipeline.stages.extract_baseline import _output_to_baseline_json

        output = BaselinePatrimonialOutput(**golden_data)
        baseline = _output_to_baseline_json(output)

        assert baseline["resumo"]["patrimonio_liquido"] == 897000.00
        assert len(baseline["itens"]) == 5
        assert baseline["_meta"]["source"] == "E1.5-llm"
        assert baseline["itens"][0]["categoria"] == "imovel"

    def test_items_sum_matches_total(self, golden_data):
        total = sum(i["value_brl"] for i in golden_data["items"])
        assert abs(total - golden_data["total_assets_brl"]) < 0.01


class TestE2LLMGoldenFile:
    @pytest.fixture
    def golden_data(self):
        return json.loads((GOLDEN_DIR / "e2_llm_extract_output.json").read_text())

    def test_schema_parses(self, golden_data):
        from pipeline.llm.schemas.e2_llm_extract import LLMExtractOutput

        output = LLMExtractOutput(**golden_data)
        assert len(output.transactions) == 2
        assert len(output.investments) == 3
        assert output.institution == "btgpactual"

    def test_validator_accepts(self, golden_data):
        from pipeline.llm.schemas.e2_llm_extract import LLMExtractOutput
        from pipeline.llm.validators import validate_e2_llm_output

        output = LLMExtractOutput(**golden_data)
        result = validate_e2_llm_output(output)
        assert result.valid, f"Errors: {result.errors}"

    def test_output_converter(self, golden_data):
        from pipeline.llm.schemas.e2_llm_extract import LLMExtractOutput
        from pipeline.stages.extract_with_llm import _output_to_e2_json

        output = LLMExtractOutput(**golden_data)
        e2 = _output_to_e2_json(output)

        assert e2["extraido_por"] == "llm"
        assert e2["instituicao"] == "btgpactual"
        assert e2["periodo"] == {"inicio": "2024-12-01", "fim": "2024-12-31"}
        assert len(e2["transacoes"]) == 2
        assert len(e2["investimentos"]) == 3
        assert e2["investimentos"][0]["taxa"] == "100% CDI"

    def test_transactions_have_valid_dates(self, golden_data):
        import re

        date_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        for t in golden_data["transactions"]:
            assert date_re.match(t["date"]), f"Invalid date: {t['date']}"

    def test_investments_have_positive_values(self, golden_data):
        for inv in golden_data["investments"]:
            assert inv["value_brl"] > 0


class TestE7ReviewGoldenFile:
    @pytest.fixture
    def golden_data(self):
        return json.loads((GOLDEN_DIR / "e7_review_output.json").read_text())

    def test_schema_parses(self, golden_data):
        from pipeline.llm.schemas.e7_review import E7ReviewOutput

        output = E7ReviewOutput(**golden_data)
        assert len(output.insights) == 3
        assert len(output.recommendations) == 3
        assert output.risk_level == "moderate"
        assert output.confidence == 0.85

    def test_output_converter(self, golden_data):
        from pipeline.llm.schemas.e7_review import E7ReviewOutput
        from pipeline.stages.review_finances import _output_to_review_json

        output = E7ReviewOutput(**golden_data)
        result = _output_to_review_json(output)

        assert result["nivel_risco"] == "moderate"
        assert len(result["insights"]) == 3
        assert len(result["recomendacoes"]) == 3
        assert len(result["ajustes_score"]) == 2
        assert "resumo_executivo" in result["narrativas"]
        assert "patrimonio_analise" in result["narrativas"]

    def test_insights_have_valid_categories(self, golden_data):
        valid = {
            "patrimonio",
            "fluxo_caixa",
            "investimentos",
            "endividamento",
            "planejamento",
            "score",
        }
        for ins in golden_data["insights"]:
            assert ins["category"] in valid, f"Invalid category: {ins['category']}"

    def test_insights_have_valid_severities(self, golden_data):
        valid = {"info", "attention", "warning", "critical"}
        for ins in golden_data["insights"]:
            assert ins["severity"] in valid, f"Invalid severity: {ins['severity']}"

    def test_risk_level_valid(self, golden_data):
        valid = {"low", "moderate", "high", "critical"}
        assert golden_data["risk_level"] in valid
