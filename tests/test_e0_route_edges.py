#!/usr/bin/env python3
"""Edge-case unit tests for E0-route helpers (7D.1)."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.route_documents import (
    _validate_period,
    build_final_name,
    classify_by_llm,
    extract_period,
)


class TestValidatePeriod:
    def test_valid_month(self):
        assert _validate_period("202604") is True

    def test_invalid_month_13(self):
        assert _validate_period("202613") is False

    def test_wrong_length(self):
        assert _validate_period("20260") is False


class TestExtractPeriod:
    def test_fallback_to_yyyymmdd_when_no_match(self, monkeypatch):
        from datetime import date as real_date

        class _FixedDate:
            @staticmethod
            def today():
                return real_date(2026, 4, 17)

        monkeypatch.setattr("scripts.route_documents.date", _FixedDate)
        assert extract_period("no_period_here.pdf") == "20260417"


class TestBuildFinalName:
    def test_llm_final_name_sanitized(self):
        name = build_final_name(
            {
                "source": "llm",
                "final_name": "../../evil.pdf",
                "dest_group": "members",
                "doc_type": "holerite",
                "period": "202604",
                "member": "titular",
            },
            ".pdf",
        )
        assert ".." not in name
        assert name.endswith(".pdf")

    def test_bank_statement_pattern(self):
        n = build_final_name(
            {
                "source": "regex",
                "dest_group": "banking",
                "institution": "itau",
                "doc_type": "extrato",
                "period": "202604",
            },
            ".pdf",
        )
        assert n.startswith("itau_extrato_202604")
        assert n.endswith("-0_original.pdf")


class TestBuildFinalNameContentHash:
    """ADR-084 — content-addressed uploads: sha256[:12] prefix."""

    _CLF = {
        "source": "regex",
        "dest_group": "banking",
        "institution": "itau",
        "doc_type": "extrato",
        "period": "202604",
    }

    def test_hash_prefix_prepended_when_provided(self):
        n = build_final_name(self._CLF, ".pdf", content_hash="a" * 64)
        assert n.startswith("aaaaaaaaaaaa_itau_extrato_202604")
        assert n.endswith("-0_original.pdf")

    def test_no_prefix_when_hash_absent(self):
        n = build_final_name(self._CLF, ".pdf")
        assert n.startswith("itau_extrato_202604")
        assert "_itau_extrato" not in n[:1]  # no accidental leading underscore

    def test_prefix_is_exactly_12_chars(self):
        n = build_final_name(self._CLF, ".pdf", content_hash="0123456789abcdef" * 4)
        # First 12 chars of the hash + underscore + rest
        assert n.startswith("0123456789ab_")

    def test_same_hash_same_filename(self):
        h = "deadbeefcafef00d" * 4
        n1 = build_final_name(self._CLF, ".pdf", content_hash=h)
        n2 = build_final_name(self._CLF, ".pdf", content_hash=h)
        assert n1 == n2

    def test_different_hash_different_filename(self):
        clf = dict(self._CLF)
        n1 = build_final_name(clf, ".pdf", content_hash="a" * 64)
        n2 = build_final_name(clf, ".pdf", content_hash="b" * 64)
        assert n1 != n2

    def test_hash_applied_to_llm_final_name(self):
        name = build_final_name(
            {
                "source": "llm",
                "final_name": "itau_extrato_202604-0_original.pdf",
                "dest_group": "banking",
                "doc_type": "extrato",
                "institution": "itau",
                "period": "202604",
            },
            ".pdf",
            content_hash="c" * 64,
        )
        assert name.startswith("cccccccccccc_")

    def test_hash_applied_to_members_pattern(self):
        name = build_final_name(
            {
                "source": "regex",
                "dest_group": "members",
                "doc_type": "holerite",
                "member": "titular",
                "period": "202604",
            },
            ".pdf",
            content_hash="1234567890ab" + "0" * 52,
        )
        assert name.startswith("1234567890ab_titular_holerite_202604")


_FAKE_LLM_JSON = {
    "institution": "c6bank",
    "doc_type": "extratoconta",
    "dest_group": "financial_statements",
    "period": "202601",
    "member": None,
    "final_name": "c6bank_extratoconta_202601-0_original.jpg",
    "confidence": 0.95,
}


def _fake_anthropic_client(captured: list) -> MagicMock:
    client = MagicMock()
    response = MagicMock()
    response.content = [MagicMock(text=json.dumps(_FAKE_LLM_JSON))]
    client.messages.create.side_effect = lambda **kw: captured.append(kw["messages"]) or response
    return client


def _extract_prompt_text(messages: list) -> str:
    content = messages[0]["content"]
    blocks = content if isinstance(content, list) else [{"type": "text", "text": content}]
    return next(b["text"] for b in blocks if b.get("type") == "text")


def _run_classify_by_llm_with_image(tmp_path: Path, ext: str, monkeypatch) -> list:
    img = tmp_path / f"002{ext}"
    img.write_bytes(b"\xff\xd8\xff\xe0fake-jpeg-bytes")
    captured: list = []
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-fake-key")
    with patch("anthropic.Anthropic", return_value=_fake_anthropic_client(captured)):
        classify_by_llm(img)
    assert captured, "LLM should have been called"
    return captured[0]


class TestClassifyByLlmImagePrompt:
    """Regressão: prompt de visão para JPG/PNG não pode ser mangled (str.replace('', X) bug)."""

    def test_jpg_prompt_is_not_mangled(self, tmp_path, monkeypatch):
        messages = _run_classify_by_llm_with_image(tmp_path, ".jpg", monkeypatch)
        prompt_text = _extract_prompt_text(messages)
        # Bug antigo: placeholder repetido entre caracteres. Sadio: aparece 1×.
        count = prompt_text.count("[Conteúdo visual enviado acima]")
        assert count == 1, f"Prompt mangled — placeholder×{count}, len={len(prompt_text)}"
        assert len(prompt_text) < 5000
        assert "Analise o arquivo abaixo" in prompt_text
        assert "Classifique o arquivo retornando APENAS um JSON" in prompt_text

    def test_jpg_image_attached_via_vision_api(self, tmp_path, monkeypatch):
        messages = _run_classify_by_llm_with_image(tmp_path, ".jpg", monkeypatch)
        image_blocks = [b for b in messages[0]["content"] if b.get("type") == "image"]
        assert len(image_blocks) == 1
        assert image_blocks[0]["source"]["media_type"] == "image/jpeg"

    def test_png_prompt_is_not_mangled(self, tmp_path, monkeypatch):
        messages = _run_classify_by_llm_with_image(tmp_path, ".png", monkeypatch)
        prompt_text = _extract_prompt_text(messages)
        assert prompt_text.count("[Conteúdo visual enviado acima]") == 1
        assert len(prompt_text) < 5000
