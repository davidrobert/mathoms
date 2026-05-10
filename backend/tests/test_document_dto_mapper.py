"""Testes unitários do mapper DTO do agregado Document.

Cobrem:

- ``document_to_response`` mapeia ORM → DTO preservando todos os
  campos (incluindo os de pipeline incremental: ``pipeline_last_run_at``,
  ``pipeline_e2_extract_ok``, ``pipeline_extract_notes``).
- Enums ``DocumentStatus`` / ``DocumentType`` sobrevivem ao round-trip.
- ``classification_meta`` dict passa intacto (sem reformatação).
- Campos opcionais ``None`` viram ``None`` no DTO.
- Mapper funciona sem ``AsyncSession``.
- Command ``DocumentUpdateCommand`` trata empty-string como ``None``
  (paridade com o ``DocumentUpdateRequest`` legado).
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from backend.app.models.document import DocumentStatus, DocumentType
from backend.app.schemas.dto.document.command import DocumentUpdateCommand
from backend.app.schemas.dto.document.mapper import _extract_e0_doc_type, document_to_response


def _fake_doc(**overrides) -> SimpleNamespace:
    defaults = dict(
        id="doc-1",
        workspace_id="ws-1",
        original_name="extrato_itau_202601.pdf",
        stored_path="ws-1/uploads/extrato_itau_202601.pdf",
        doc_type=DocumentType.bank_statement,
        bank_code="itau",
        period="202601",
        status=DocumentStatus.ready,
        classification_meta=None,
        classification_confidence=None,
        needs_review=False,
        possible_duplicate_of_id=None,
        file_size_bytes=123456,
        content_hash="abc123",
        content_type="application/pdf",
        error_message=None,
        uploaded_at=datetime(2026, 1, 15, 10, 30, tzinfo=timezone.utc),
        pipeline_last_run_at=None,
        pipeline_e2_extract_ok=None,
        pipeline_extract_notes=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestDocumentToResponse:
    def test_minimal_document(self):
        doc = _fake_doc()

        resp = document_to_response(doc)

        assert resp.id == "doc-1"
        assert resp.workspace_id == "ws-1"
        assert resp.original_name == "extrato_itau_202601.pdf"
        assert resp.doc_type == DocumentType.bank_statement
        assert resp.status == DocumentStatus.ready
        assert resp.needs_review is False

    def test_classification_meta_dict_preserved(self):
        meta = {
            "source": "content_regex",
            "matches": ["itau", "extrato"],
            "manual_override": {"at": "2026-01-15T11:00:00Z", "by": "user-1"},
        }
        doc = _fake_doc(
            classification_meta=meta,
            classification_confidence=0.92,
        )

        resp = document_to_response(doc)

        # O shape deve passar intacto — mapper não reformata.
        assert resp.classification_meta == meta
        assert resp.classification_confidence == 0.92

    def test_enum_values_survive_roundtrip(self):
        doc = _fake_doc(
            doc_type=DocumentType.credit_card_bill,
            status=DocumentStatus.needs_password,
        )

        resp = document_to_response(doc)

        assert resp.doc_type == DocumentType.credit_card_bill
        assert resp.status == DocumentStatus.needs_password

    def test_e0_doc_type_derived_from_meta_content(self):
        meta = {"content": {"doc_type": "informerendimentosaluguel"}, "confidence": 1.0}
        resp = document_to_response(_fake_doc(classification_meta=meta))
        assert resp.e0_doc_type == "informerendimentosaluguel"

    def test_e0_doc_type_falls_back_to_llm_when_content_empty(self):
        meta = {"content": {"doc_type": None}, "llm": {"doc_type": "extratoconta"}}
        resp = document_to_response(_fake_doc(classification_meta=meta))
        assert resp.e0_doc_type == "extratoconta"

    def test_e0_doc_type_none_when_meta_absent(self):
        resp = document_to_response(_fake_doc(classification_meta=None))
        assert resp.e0_doc_type is None

    def test_all_optional_fields_none(self):
        doc = _fake_doc(
            stored_path=None,
            doc_type=None,
            bank_code=None,
            period=None,
            classification_meta=None,
            classification_confidence=None,
            possible_duplicate_of_id=None,
            file_size_bytes=None,
            content_type=None,
            error_message=None,
            pipeline_last_run_at=None,
            pipeline_e2_extract_ok=None,
            pipeline_extract_notes=None,
        )

        resp = document_to_response(doc)

        assert resp.stored_path is None
        assert resp.doc_type is None
        assert resp.bank_code is None
        assert resp.period is None
        assert resp.classification_meta is None
        assert resp.classification_confidence is None
        assert resp.possible_duplicate_of_id is None
        assert resp.file_size_bytes is None
        assert resp.content_type is None
        assert resp.error_message is None
        assert resp.pipeline_last_run_at is None
        assert resp.pipeline_e2_extract_ok is None
        assert resp.pipeline_extract_notes is None

    def test_pipeline_incremental_fields_roundtrip(self):
        """Os 3 campos de pipeline incremental (ADR-080) são parte do DTO."""
        run_at = datetime(2026, 1, 20, 14, 45, tzinfo=timezone.utc)
        doc = _fake_doc(
            status=DocumentStatus.processed,
            pipeline_last_run_at=run_at,
            pipeline_e2_extract_ok=True,
            pipeline_extract_notes="Linhas 42–45 ignoradas (vazias).",
        )

        resp = document_to_response(doc)

        assert resp.pipeline_last_run_at == run_at
        assert resp.pipeline_e2_extract_ok is True
        assert resp.pipeline_extract_notes == "Linhas 42–45 ignoradas (vazias)."

    def test_needs_review_and_possible_duplicate_pointer(self):
        doc = _fake_doc(
            needs_review=True,
            possible_duplicate_of_id="doc-original",
        )

        resp = document_to_response(doc)

        assert resp.needs_review is True
        assert resp.possible_duplicate_of_id == "doc-original"

    def test_error_status_with_error_message(self):
        doc = _fake_doc(
            status=DocumentStatus.error,
            error_message="Arquivo corrompido no upload",
            stored_path=None,
            doc_type=None,
        )

        resp = document_to_response(doc)

        assert resp.status == DocumentStatus.error
        assert resp.error_message == "Arquivo corrompido no upload"


class TestExtractE0DocType:
    def test_returns_none_when_meta_missing(self):
        assert _extract_e0_doc_type(None) is None
        assert _extract_e0_doc_type({}) is None

    def test_prefers_content_over_llm(self):
        meta = {
            "content": {"doc_type": "informerendimentosaluguel"},
            "llm": {"doc_type": "outro"},
        }
        assert _extract_e0_doc_type(meta) == "informerendimentosaluguel"


class TestDocumentUpdateCommand:
    """DTO de entrada ``PATCH /documents/{id}`` — paridade com ``DocumentUpdateRequest``."""

    def test_empty_body_is_valid(self):
        # Todos os campos opcionais — o router é que rejeita body sem nenhum campo setado.
        cmd = DocumentUpdateCommand()
        assert cmd.doc_type is None
        assert cmd.bank_code is None
        assert cmd.period is None

    def test_partial_update_only_affects_set_fields(self):
        cmd = DocumentUpdateCommand(bank_code="itau")
        dumped = cmd.model_dump(exclude_unset=True)
        assert dumped == {"bank_code": "itau"}

    def test_empty_string_bank_code_becomes_none(self):
        # Paridade com validator legado: strip vazio → None.
        cmd = DocumentUpdateCommand(bank_code="   ", period="")
        assert cmd.bank_code is None
        assert cmd.period is None

    def test_doc_type_accepts_enum(self):
        cmd = DocumentUpdateCommand(doc_type=DocumentType.credit_card_bill)
        assert cmd.doc_type == DocumentType.credit_card_bill

    def test_doc_type_accepts_string_value(self):
        cmd = DocumentUpdateCommand(doc_type="bank_statement")
        assert cmd.doc_type == DocumentType.bank_statement

    def test_invalid_doc_type_rejected(self):
        with pytest.raises(ValueError):
            DocumentUpdateCommand(doc_type="banco_inexistente")

    def test_bank_code_too_long_rejected(self):
        with pytest.raises(ValueError):
            DocumentUpdateCommand(bank_code="x" * 51)

    def test_period_too_long_rejected(self):
        with pytest.raises(ValueError):
            DocumentUpdateCommand(period="y" * 51)
