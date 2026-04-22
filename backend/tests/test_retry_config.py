"""Tests for stage retry configuration — Phase 5C.5."""

import pytest

from backend.app.services.retry_config import (
    STAGE_RETRY_CONFIGS,
    StageRetryConfig,
    get_retry_config,
)


class TestStageRetryConfig:
    def test_default_no_retries(self):
        cfg = StageRetryConfig()
        assert cfg.max_retries == 0
        assert cfg.should_retry(0, "any error") is False

    def test_should_retry_within_limit(self):
        cfg = StageRetryConfig(max_retries=3, retryable_errors=["timeout"])
        assert cfg.should_retry(0, "Connection timeout") is True
        assert cfg.should_retry(1, "timeout error") is True
        assert cfg.should_retry(2, "timeout") is True
        assert cfg.should_retry(3, "timeout") is False

    def test_should_retry_non_retryable_error(self):
        cfg = StageRetryConfig(max_retries=3, retryable_errors=["timeout"])
        assert cfg.should_retry(0, "Parser crash: invalid PDF") is False

    def test_should_retry_no_error_patterns(self):
        """When no retryable_errors specified, retry any error up to max_retries."""
        cfg = StageRetryConfig(max_retries=2)
        assert cfg.should_retry(0, "any error") is True
        assert cfg.should_retry(1, "different error") is True
        assert cfg.should_retry(2, "still error") is False

    def test_delay_for_attempt(self):
        cfg = StageRetryConfig(retry_delay_seconds=5.0, backoff_factor=2.0)
        assert cfg.delay_for_attempt(0) == 5.0
        assert cfg.delay_for_attempt(1) == 10.0
        assert cfg.delay_for_attempt(2) == 20.0

    def test_case_insensitive_error_matching(self):
        cfg = StageRetryConfig(max_retries=1, retryable_errors=["TIMEOUT"])
        assert cfg.should_retry(0, "connection timeout occurred") is True

    def test_multiple_retryable_errors(self):
        cfg = StageRetryConfig(max_retries=2, retryable_errors=["timeout", "rate_limit", "503"])
        assert cfg.should_retry(0, "Rate limit exceeded") is True
        assert cfg.should_retry(0, "HTTP 503 Service Unavailable") is True
        assert cfg.should_retry(0, "timeout waiting for response") is True
        assert cfg.should_retry(0, "Invalid JSON format") is False


class TestGetRetryConfig:
    def test_llm_stages_have_retries(self):
        for stage in ["E1", "E1.5", "E2-llm", "E7-review"]:
            cfg = get_retry_config(stage)
            assert cfg.max_retries > 0, f"{stage} should have retries configured"

    def test_deterministic_stages_no_retries(self):
        for stage in ["E0-audit", "E0-route", "E2", "E3", "E4", "E5", "E6"]:
            cfg = get_retry_config(stage)
            assert cfg.max_retries == 0, f"{stage} should have 0 retries"

    def test_e7_review_has_lower_retries(self):
        cfg = get_retry_config("E7-review")
        e1_cfg = get_retry_config("E1")
        assert cfg.max_retries <= e1_cfg.max_retries

    def test_retryable_errors_include_common_transients(self):
        for stage in STAGE_RETRY_CONFIGS:
            cfg = STAGE_RETRY_CONFIGS[stage]
            errors = [e.lower() for e in cfg.retryable_errors]
            assert "timeout" in errors, f"{stage} should retry on timeout"
            assert "rate_limit" in errors, f"{stage} should retry on rate_limit"
