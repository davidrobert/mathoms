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
        from scripts import route_documents

        monkeypatch.setattr(route_documents, "classify_by_llm", lambda _path: None)

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
        from scripts import route_documents

        monkeypatch.setattr(route_documents, "classify_by_llm", lambda _p: _FAKE_LLM_RESULT)

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
        from scripts import route_documents

        def _raise(_path):
            raise RuntimeError("boom")

        monkeypatch.setattr(route_documents, "classify_by_llm", _raise)

        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4\n")
        result = dc.classify_document(f, tmp_path, use_llm=True)
        meta = result["classification_meta"]
        assert "RuntimeError" in meta.get("llm_error", "")
        assert "llm_skipped_reason" not in meta


class TestExtratoMissingInstitutionGate:
    """Gate de invariante: ``extratoconta*``/``extratopoupanca*`` sem ``bank_code``
    força ``needs_review=True``. Sem isso, o LLM (E0 fallback) pode retornar
    confidence=1.0 com institution=None — observado no workspace 5@5.com,
    causando duplicação cross-document que escapa do dedup K4 (ADR-255)."""

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

        from backend.app.services import content_classifier

        monkeypatch.setattr(content_classifier, "classify_file", _fake_classify_file)

    def _run(self, tmp_path, monkeypatch, llm_payload):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
        from scripts import route_documents

        monkeypatch.setattr(route_documents, "classify_by_llm", lambda _p: llm_payload)
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4\n")
        return dc.classify_document(f, tmp_path, use_llm=True)

    def test_extratoconta_without_institution_forces_review(
        self, tmp_path, monkeypatch, force_low_confidence_regex
    ):
        """Caso real do workspace 5@5.com: extrato-da-sua-conta-ULID.pdf
        classificado pelo LLM como extratoconta+confidence=1.0 mas
        institution=None. Sem esse gate, vira needs_review=False, é roteado
        para extração, e gera txs com banco vazio que duplicam pix Arvo."""
        payload = {
            "doc_type": "extratoconta",
            "institution": None,
            "period": "202505",
            "dest_group": "financial_statements",
            "confidence": 1.0,
        }
        result = self._run(tmp_path, monkeypatch, payload)
        assert result["needs_review"] is True
        meta = result["classification_meta"]
        assert meta["needs_review_reason"] == "missing_institution_for_bank_statement"

    def test_extratoconta_with_institution_does_not_force_review(
        self, tmp_path, monkeypatch, force_low_confidence_regex
    ):
        payload = {
            "doc_type": "extratoconta",
            "institution": "itau",
            "period": "202604",
            "dest_group": "financial_statements",
            "confidence": 0.95,
        }
        result = self._run(tmp_path, monkeypatch, payload)
        assert result["needs_review"] is False
        meta = result["classification_meta"]
        assert "needs_review_reason" not in meta

    def test_non_extratoconta_without_institution_not_affected(
        self, tmp_path, monkeypatch, force_low_confidence_regex
    ):
        """``irpfdeclaracao`` sem institution é normal (Receita Federal vem
        de outra heurística e o gate não se aplica)."""
        payload = {
            "doc_type": "irpfdeclaracao",
            "institution": None,
            "period": "2025",
            "dest_group": "income_tax_br",
            "confidence": 0.9,
        }
        result = self._run(tmp_path, monkeypatch, payload)
        assert result["needs_review"] is False


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


def _patch_classify_file(monkeypatch, *, doc_type: str, institution: str) -> None:
    from backend.app.services import content_classifier
    from backend.app.services.content_classifier import ContentClassification

    def _fake_classify_file(filepath, _preview):
        return ContentClassification(
            doc_type=doc_type,
            dest_group=None,
            institution=institution,
            period="202606",
            confidence=0.95,
            source="content_regex",
        )

    monkeypatch.setattr(content_classifier, "classify_file", _fake_classify_file)


class TestOtherWithoutPipelineGate:
    """A28.l8 — código E0 que mapeia para ``DocumentType.other`` sem stage
    consumidor (dogfood: Binance CSV, informe Stone PJ) vira needs_review com
    motivo acionável, nunca sai do pipeline em silêncio."""

    def test_unmapped_code_maps_to_other_without_pipeline(self):
        assert dc.maps_to_other_without_pipeline("extratocripto") is True
        assert dc.maps_to_other_without_pipeline("informe_stone_pj") is True

    def test_intentional_other_codes_are_not_flagged(self):
        # ADR-216: aluguel vive em .other por design (stage próprio).
        assert dc.maps_to_other_without_pipeline("faturaaluguel") is False
        assert dc.maps_to_other_without_pipeline("informerendimentosaluguel2024") is False

    def test_mapped_codes_are_not_flagged(self):
        assert dc.maps_to_other_without_pipeline("extratocontabrl") is False
        assert dc.maps_to_other_without_pipeline("irpfdeclaracao") is False
        assert dc.maps_to_other_without_pipeline(None) is False

    def test_classify_document_flags_other_without_pipeline(self, tmp_path, monkeypatch):
        # Ex.: Binance CSV — regex de conteúdo reconhece com confidence alta,
        # mas o código não tem parser/stage (cai em .other).
        _patch_classify_file(monkeypatch, doc_type="extratocripto", institution="binance")
        f = tmp_path / "binance.csv"
        f.write_text("data,valor\n")

        result = dc.classify_document(f, tmp_path, use_llm=False)

        assert result["doc_type"] == DocumentType.other
        assert result["needs_review"] is True
        reason = result["classification_meta"]["needs_review_reason"]
        assert reason.startswith("doc_type_sem_pipeline:extratocripto")
