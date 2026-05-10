"""P2 — classificação unificada: modelo, mapa de tipos, gate de roteamento."""

import sys

import pytest

from backend.app.models.document import DocumentType
from backend.app.services import document_classification as dc
from backend.app.services.document_classification import (
    ClassificationResult,
    _llm_prerequisites_skip_reason,
    classification_can_route_to_data,
    document_type_to_e0_dest,
    map_e0_doc_type_to_document_type,
)


def test_map_e0_extrato_to_bank_statement():
    assert map_e0_doc_type_to_document_type("extratocontabrl") == DocumentType.bank_statement


def test_map_e0_fatura_to_credit_card():
    assert map_e0_doc_type_to_document_type("faturaunique") == DocumentType.credit_card_bill


def test_map_e0_cdb_to_investment():
    assert map_e0_doc_type_to_document_type("cdbdetalhesdi1") == DocumentType.investment_report


def test_classification_can_route_requires_dest_and_e0_type():
    assert not classification_can_route_to_data(
        {"needs_review": False, "dest_group": "extratos", "e0_doc_type": None}
    )
    assert not classification_can_route_to_data(
        {"needs_review": False, "dest_group": None, "e0_doc_type": "x"}
    )
    assert classification_can_route_to_data(
        {"needs_review": False, "dest_group": "extratos", "e0_doc_type": "extratocontabrl"}
    )


def test_needs_review_blocks_route():
    assert not classification_can_route_to_data(
        {
            "needs_review": True,
            "dest_group": "extratos",
            "e0_doc_type": "extratocontabrl",
        }
    )


def test_document_type_to_e0_dest_roundtrip():
    """Reverse mapping precisa casar com forward mapping para todo tipo suportado."""
    cases = [
        DocumentType.bank_statement,
        DocumentType.credit_card_bill,
        DocumentType.investment_report,
        DocumentType.irpf,
    ]
    for dt in cases:
        e0_dest = document_type_to_e0_dest(dt)
        assert e0_dest is not None, f"Sem reverse mapping para {dt}"
        e0_code, dest_group = e0_dest
        assert dest_group  # truthy
        assert map_e0_doc_type_to_document_type(e0_code) == dt


def test_document_type_to_e0_dest_returns_none_for_other():
    assert document_type_to_e0_dest(DocumentType.other) is None
    assert document_type_to_e0_dest(DocumentType.e1_members_json) is None
    assert document_type_to_e0_dest(DocumentType.e1_5_baseline_json) is None


def test_document_type_to_e0_dest_investment_uses_canonical_code():
    """Investment_report → ``investimentosposicao`` (não cdb*); E2 reconhece esse prefixo."""
    e0_code, dest_group = document_type_to_e0_dest(DocumentType.investment_report)
    assert e0_code == "investimentosposicao"
    assert dest_group == "financial_statements"


class TestLLMPrerequisitesSkipReason:
    """``_llm_prerequisites_skip_reason`` distingue SDK ausente, key ausente e OK."""

    def test_returns_none_when_sdk_and_key_present(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
        # SDK is required to be importable in test env (it's a real dep).
        assert _llm_prerequisites_skip_reason() is None

    def test_returns_missing_api_key_when_env_unset(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        assert _llm_prerequisites_skip_reason() == "missing_api_key"

    def test_returns_missing_api_key_when_env_empty_string(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        assert _llm_prerequisites_skip_reason() == "missing_api_key"

    def test_returns_sdk_not_installed_when_import_fails(self, monkeypatch):
        # Simula SDK ausente removendo `anthropic` de sys.modules e fazendo
        # qualquer re-import dele estourar ImportError.
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
        monkeypatch.setitem(sys.modules, "anthropic", None)
        assert _llm_prerequisites_skip_reason() == "sdk_not_installed"


_FAKE_LLM_RESULT = {
    "doc_type": "extratoconta",
    "institution": "itau",
    "period": "202604",
    "dest_group": "financial_statements",
    "confidence": 0.9,
}


class TestClassifyDocumentLLMSkipMeta:
    """``classify_document`` propaga ``llm_skipped_reason`` no meta (sem PDF/rede)."""

    @pytest.fixture
    def force_low_confidence_regex(self, monkeypatch):
        from backend.app.services.content_classifier import ContentClassification

        def _fake_classify_file(filepath, _preview):
            return ContentClassification(
                doc_type=None,
                dest_group=None,
                institution=None,
                period=None,
                confidence=0.0,
                source="content_regex",
            )

        monkeypatch.setattr(dc, "classify_file", _fake_classify_file, raising=False)
        # classify_file vem de import dentro da função; patcheamos no módulo origem.
        from backend.app.services import content_classifier

        monkeypatch.setattr(content_classifier, "classify_file", _fake_classify_file)

    def test_skip_reason_when_api_key_missing(
        self, tmp_path, monkeypatch, force_low_confidence_regex
    ):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4\n")
        result = dc.classify_document(f, tmp_path, use_llm=True)
        meta = result["classification_meta"]
        assert meta.get("llm_skipped_reason") == "missing_api_key"
        assert "llm" not in meta or meta.get("llm") is None
        assert "llm_error" not in meta

    def test_skip_reason_no_result_when_llm_returns_none(
        self, tmp_path, monkeypatch, force_low_confidence_regex
    ):
        """LLM disponível mas devolve None (confidence baixa, JSON inválido,
        retry esgotado): o caminho silencioso vira ``no_result`` no meta."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
        from scripts import e0_route

        monkeypatch.setattr(e0_route, "classify_by_llm", lambda _path: None)

        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4\n")
        result = dc.classify_document(f, tmp_path, use_llm=True)
        meta = result["classification_meta"]
        assert meta.get("llm_skipped_reason") == "no_result"
        assert "llm_error" not in meta

    def test_no_skip_reason_when_llm_succeeds(
        self, tmp_path, monkeypatch, force_low_confidence_regex
    ):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
        from scripts import e0_route

        monkeypatch.setattr(e0_route, "classify_by_llm", lambda _p: _FAKE_LLM_RESULT)

        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4\n")
        result = dc.classify_document(f, tmp_path, use_llm=True)
        meta = result["classification_meta"]
        assert "llm_skipped_reason" not in meta
        assert meta.get("llm", {}).get("doc_type") == "extratoconta"

    def test_llm_error_takes_precedence_over_no_result(
        self, tmp_path, monkeypatch, force_low_confidence_regex
    ):
        """Quando ``classify_by_llm`` lança exceção, ``llm_error`` é gravado e
        ``llm_skipped_reason`` NÃO entra em colisão (precedência da exceção)."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
        from scripts import e0_route

        def _raise(_path):
            raise RuntimeError("boom")

        monkeypatch.setattr(e0_route, "classify_by_llm", _raise)

        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4\n")
        result = dc.classify_document(f, tmp_path, use_llm=True)
        meta = result["classification_meta"]
        assert "RuntimeError" in meta.get("llm_error", "")
        assert "llm_skipped_reason" not in meta


def test_classification_result_roundtrip_dict():
    r = ClassificationResult(
        doc_type=DocumentType.bank_statement,
        bank_code="itau",
        period="2026-04",
        dest_group="extratos",
        e0_doc_type="extratocontabrl",
        classification_meta={"source": "test"},
        confidence=0.95,
        needs_review=False,
    )
    d = r.as_dict()
    assert d["doc_type"] == DocumentType.bank_statement
    assert d["e0_doc_type"] == "extratocontabrl"
    assert d["confidence"] == 0.95
