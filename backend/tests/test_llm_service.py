"""Tests for Phase 4A: LLMService, error classification, retry, token tracking, text extractor."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from pipeline.llm.service import (
    LLMConfig,
    LLMCallResult,
    LLMError,
    LLMErrorType,
    LLMRunSummary,
    LLMService,
    LLMValidationError,
    _classify_error,
)
from pipeline.llm.text_extractor import DocumentTextExtractor
from backend.tests.fakes.fake_llm_client import FakeLLMClient


# =============================================================================
# Error classification tests
# =============================================================================


class TestErrorClassification:
    def test_auth_error(self):
        assert _classify_error(Exception("Authentication failed")) == LLMErrorType.auth
        assert _classify_error(Exception("Invalid API key")) == LLMErrorType.auth
        assert _classify_error(Exception("Unauthorized")) == LLMErrorType.auth

    def test_rate_limit_error(self):
        assert _classify_error(Exception("Rate limit exceeded")) == LLMErrorType.rate_limit
        assert _classify_error(Exception("429 Too Many Requests")) == LLMErrorType.rate_limit

    def test_timeout_error(self):
        assert _classify_error(Exception("Request timed out")) == LLMErrorType.timeout
        assert _classify_error(Exception("Connection timeout")) == LLMErrorType.timeout

    def test_context_length_error(self):
        assert _classify_error(Exception("Context length exceeded")) == LLMErrorType.context_length
        assert _classify_error(Exception("Input too long for maximum context")) == LLMErrorType.context_length

    def test_validation_error(self):
        assert _classify_error(Exception("Pydantic validation failed")) == LLMErrorType.validation

    def test_unknown_error(self):
        assert _classify_error(Exception("Something weird")) == LLMErrorType.provider_error


# =============================================================================
# LLMConfig tests
# =============================================================================


class TestLLMConfig:
    def test_defaults(self):
        cfg = LLMConfig()
        assert cfg.provider == "anthropic"
        assert cfg.model_name == "claude-sonnet-4-20250514"
        assert cfg.max_tokens == 4096
        assert cfg.temperature == 0.1

    def test_custom_values(self):
        cfg = LLMConfig(provider="openai", api_key="sk-test", model_name="gpt-4o", max_tokens=8192, temperature=0.5)
        assert cfg.provider == "openai"
        assert cfg.api_key == "sk-test"
        assert cfg.model_name == "gpt-4o"


# =============================================================================
# LLMRunSummary tests
# =============================================================================


class TestLLMRunSummary:
    def test_empty_summary(self):
        s = LLMRunSummary()
        assert s.total_tokens_in == 0
        assert s.total_tokens_out == 0
        assert s.total_cost_usd == 0.0
        assert s.total_duration_ms == 0
        d = s.to_dict()
        assert d["total_calls"] == 0

    def test_aggregation(self):
        s = LLMRunSummary(calls=[
            LLMCallResult(output=None, provider="anthropic", model="claude", tokens_in=100, tokens_out=50, cost_estimate_usd=0.001, duration_ms=500),
            LLMCallResult(output=None, provider="anthropic", model="claude", tokens_in=200, tokens_out=100, cost_estimate_usd=0.002, duration_ms=800),
        ])
        assert s.total_tokens_in == 300
        assert s.total_tokens_out == 150
        assert abs(s.total_cost_usd - 0.003) < 0.0001
        assert s.total_duration_ms == 1300

        d = s.to_dict()
        assert d["total_calls"] == 2


# =============================================================================
# LLMService model string tests
# =============================================================================


class TestLLMServiceModelString:
    def test_anthropic_model_string(self):
        svc = LLMService(LLMConfig(provider="anthropic", model_name="claude-sonnet-4-20250514"))
        assert svc._get_model_string() == "anthropic/claude-sonnet-4-20250514"

    def test_openai_model_string(self):
        svc = LLMService(LLMConfig(provider="openai", model_name="gpt-4o"))
        assert svc._get_model_string() == "openai/gpt-4o"

    def test_unknown_provider(self):
        svc = LLMService(LLMConfig(provider="custom", model_name="my-model"))
        assert svc._get_model_string() == "my-model"


# =============================================================================
# LLMService cost estimation tests
# =============================================================================


class TestCostEstimation:
    def test_known_model(self):
        svc = LLMService(LLMConfig(model_name="claude-sonnet-4-20250514"))
        cost = svc._estimate_cost(1000, 500)
        expected = (1000 * 3.0 + 500 * 15.0) / 1_000_000
        assert abs(cost - expected) < 0.0001

    def test_unknown_model(self):
        svc = LLMService(LLMConfig(model_name="custom-model-v9"))
        cost = svc._estimate_cost(1000, 500)
        assert cost == 0.0

    def test_partial_match(self):
        svc = LLMService(LLMConfig(model_name="gpt-4o-2024-08-06"))
        cost = svc._estimate_cost(1000, 500)
        assert cost > 0


# =============================================================================
# LLMService with mock LiteLLM
# =============================================================================


class TestLLMServiceWithMock:
    @patch("pipeline.llm.service.LLMService._ensure_client")
    def test_auth_error_no_retry(self, mock_ensure):
        from pydantic import BaseModel

        class SimpleOutput(BaseModel):
            value: str

        svc = LLMService(LLMConfig(api_key="bad-key"))
        svc._client = FakeLLMClient(raises=Exception("Invalid API key"))

        with pytest.raises(LLMError) as exc_info:
            svc.call("sys", "user", SimpleOutput)

        assert exc_info.value.error_type == LLMErrorType.auth
        assert not exc_info.value.retryable


# =============================================================================
# LLMValidationError tests
# =============================================================================


class TestLLMValidationError:
    def test_has_details(self):
        err = LLMValidationError(
            "validation failed",
            last_output={"raw": "data"},
            validation_errors=["field X required", "field Y wrong type"],
        )
        assert err.error_type == LLMErrorType.validation
        assert not err.retryable
        assert err.last_output == {"raw": "data"}
        assert len(err.validation_errors) == 2


# =============================================================================
# DocumentTextExtractor tests
# =============================================================================


class TestDocumentTextExtractor:
    def test_extract_csv(self, tmp_path: Path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("date,desc,amount\n2024-01-01,Compra,100.50\n2024-01-02,Venda,-50.25\n")

        ext = DocumentTextExtractor()
        text = ext.extract(csv_file)
        assert "date,desc,amount" in text
        assert "100.50" in text
        assert "-50.25" in text

    def test_extract_json(self, tmp_path: Path):
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps({"members": [{"name": "David"}]}, indent=2))

        ext = DocumentTextExtractor()
        text = ext.extract(json_file)
        assert "David" in text

    def test_extract_txt(self, tmp_path: Path):
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Hello World\nLine 2\n")

        ext = DocumentTextExtractor()
        text = ext.extract(txt_file)
        assert "Hello World" in text

    def test_extract_unsupported(self, tmp_path: Path):
        bin_file = tmp_path / "test.bin"
        bin_file.write_bytes(b"\x00\x01\x02")

        ext = DocumentTextExtractor()
        text = ext.extract(bin_file)
        assert text == ""

    def test_csv_truncation(self, tmp_path: Path):
        csv_file = tmp_path / "big.csv"
        csv_file.write_text("x" * 200)

        ext = DocumentTextExtractor(max_chars=50)
        text = ext.extract(csv_file)
        assert len(text) <= 80  # 50 + truncation message

    def test_extract_multiple(self, tmp_path: Path):
        f1 = tmp_path / "a.csv"
        f1.write_text("a,b\n1,2\n")
        f2 = tmp_path / "b.txt"
        f2.write_text("hello")

        ext = DocumentTextExtractor()
        results = ext.extract_multiple([f1, f2])
        assert "a.csv" in results
        assert "b.txt" in results
        assert "1,2" in results["a.csv"]
        assert "hello" in results["b.txt"]

    def test_missing_file(self, tmp_path: Path):
        missing = tmp_path / "nonexistent.csv"
        ext = DocumentTextExtractor()
        text = ext.extract(missing)
        assert text == ""


# =============================================================================
# Output schema validation tests
# =============================================================================


class TestOutputSchemas:
    def test_members_extract_schema(self):
        from pipeline.llm.schemas.e1_members import MembersExtractOutput, ExtractedMember

        output = MembersExtractOutput(
            members=[ExtractedMember(key="david", full_name="David R", short_name="David", role="titular")],
            titular_key="david",
            confidence=0.95,
        )
        assert len(output.members) == 1
        assert output.confidence == 0.95

    def test_members_extract_requires_at_least_one(self):
        from pipeline.llm.schemas.e1_members import MembersExtractOutput
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            MembersExtractOutput(members=[], confidence=0.5)

    def test_baseline_schema(self):
        from pipeline.llm.schemas.e15_baseline import BaselinePatrimonialOutput, PatrimonialItem

        output = BaselinePatrimonialOutput(
            items=[PatrimonialItem(
                code="01", description="Apartamento", category="imovel",
                value_brl=500000.0, member_key="david", year=2025,
            )],
            total_assets_brl=500000.0,
            net_worth_brl=500000.0,
            reference_year=2025,
            confidence=0.9,
        )
        assert output.total_assets_brl == 500000.0

    def test_llm_extract_schema(self):
        from pipeline.llm.schemas.e2_llm_extract import LLMExtractOutput, ExtractedTransaction

        output = LLMExtractOutput(
            source_file="extrato.pdf",
            institution="itau",
            document_type="extrato",
            transactions=[ExtractedTransaction(date="2024-01-15", description="PIX", amount=-150.0)],
            confidence=0.85,
        )
        assert len(output.transactions) == 1
        assert output.transactions[0].amount == -150.0

    def test_e7_review_schema(self):
        from pipeline.llm.schemas.e7_review import E7ReviewOutput, ReviewInsight

        output = E7ReviewOutput(
            insights=[ReviewInsight(
                category="patrimonio", severity="info",
                title="Patrimônio diversificado",
                description="Boa distribuição entre classes de ativos",
            )],
            recommendations=["Aumentar reserva de emergência"],
            overall_assessment="Saúde financeira boa, com pontos de atenção em investimentos.",
            risk_level="low",
            confidence=0.9,
        )
        assert output.risk_level == "low"
        assert len(output.insights) == 1

    def test_confidence_bounds(self):
        from pipeline.llm.schemas.e1_members import MembersExtractOutput, ExtractedMember
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            MembersExtractOutput(
                members=[ExtractedMember(key="a", full_name="A", short_name="A", role="titular")],
                confidence=1.5,
            )

        with pytest.raises(ValidationError):
            MembersExtractOutput(
                members=[ExtractedMember(key="a", full_name="A", short_name="A", role="titular")],
                confidence=-0.1,
            )
