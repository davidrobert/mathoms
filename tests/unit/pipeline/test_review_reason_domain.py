"""Unit tests Fase 1 (ADR-272) — ReviewReason dataclass, redação PII e to_dict(). CPFs de teste vêm do gerador mod-11 (tests/utils/cpf), jamais CPF real (LGPD)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.review_reason import (
    ReviewReason,
    ReviewReasonCode,
    ToReviewReason,
    redact_context,
    redact_pii,
)
from tests.utils.cpf import cpf_formatted, generate_valid_cpf

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3] / "config" / "schemas" / "review_reason.schema.json"
)


def _build(**overrides) -> ReviewReason:
    base = dict(
        code=ReviewReasonCode.extract_low_confidence,
        stage="extract_statements",
        artifact_key="itau_extratoconta_202601",
        document_id=None,
        offending_value="0.62",
        expected="confidence>=0.7",
        message="confidence {value} abaixo do limiar",
        occurrence_count=1,
    )
    base.update(overrides)
    return ReviewReason(**base)


class TestRedaction:
    def test_masks_formatted_cpf(self) -> None:
        cpf = cpf_formatted(seed=7)
        out = redact_pii(f"locatário {cpf} divergente")
        assert cpf not in out
        assert "***.***.***-**" in out

    def test_masks_raw_cpf(self) -> None:
        cpf = generate_valid_cpf(seed=11)
        out = redact_pii(f"doc {cpf} sem match")
        assert cpf not in out
        assert "***.***.***-**" in out

    @pytest.mark.parametrize("money", ["1.234,56", "R$ 9.999,00", "1234,56"])
    def test_masks_brl_monetary(self, money: str) -> None:
        out = redact_pii(f"valor {money} acima do esperado")
        assert money not in out
        assert "R$ ***" in out

    def test_preserves_confidence_and_year(self) -> None:
        out = redact_pii("confidence 0.62 no ano 2024")
        assert "0.62" in out
        assert "2024" in out

    def test_idempotent(self) -> None:
        cpf = cpf_formatted(seed=3)
        once = redact_pii(f"{cpf} R$ 1.000,00")
        twice = redact_pii(once)
        assert once == twice

    def test_redact_context_recursive(self) -> None:
        cpf = cpf_formatted(seed=99)
        ctx = {
            "linha": f"PIX {cpf} 1.234,56",
            "nested": {"trecho": "transferência R$ 5.000,00"},
            "lista": [f"{cpf}", "ok"],
            "indice": 3,
        }
        red = redact_context(ctx)
        assert cpf not in json.dumps(red, ensure_ascii=False)
        assert "1.234,56" not in json.dumps(red, ensure_ascii=False)
        assert red["indice"] == 3


class TestConstruction:
    def test_post_init_redacts_offending_value(self) -> None:
        cpf = cpf_formatted(seed=5)
        rr = _build(offending_value=f"{cpf}")
        assert cpf not in rr.offending_value
        assert "***.***.***-**" in rr.offending_value

    def test_post_init_redacts_message_as_safety_net(self) -> None:
        rr = _build(message="saldo R$ 1.000,00 inconsistente")
        assert "1.000,00" not in rr.message
        assert "R$ ***" in rr.message

    def test_frozen(self) -> None:
        rr = _build()
        with pytest.raises(Exception):
            rr.code = ReviewReasonCode.dedup_possible_duplicate  # type: ignore[misc]

    def test_satisfies_protocol_check_is_structural(self) -> None:
        # ReviewReason em si NÃO é um ToReviewReason (não tem to_review_reason);
        # o protocolo é implementado por produtores na Fase 2.
        assert not isinstance(_build(), ToReviewReason)


class TestToDict:
    def test_to_dict_shape(self) -> None:
        rr = _build()
        d = rr.to_dict()
        assert d["code"] == "extract.low_confidence"
        assert set(d.keys()) == {
            "code",
            "stage",
            "artifact_key",
            "document_id",
            "offending_value",
            "expected",
            "message",
            "occurrence_count",
        }

    def test_to_dict_validates_against_schema(self) -> None:
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            pytest.skip("jsonschema não disponível — gate roda em CI")
        schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        for code in ReviewReasonCode:
            d = _build(code=code, document_id="doc-123").to_dict()
            errors = sorted(validator.iter_errors(d), key=str)
            assert not errors, f"{code}: {[e.message for e in errors]}"


class TestCodeVocabulary:
    def test_enum_matches_schema_enum(self) -> None:
        schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
        schema_codes = set(schema["properties"]["code"]["enum"])
        enum_codes = {c.value for c in ReviewReasonCode}
        assert schema_codes == enum_codes

    def test_codes_are_namespaced(self) -> None:
        for c in ReviewReasonCode:
            assert "." in c.value, f"{c.value} não é namespaced"
