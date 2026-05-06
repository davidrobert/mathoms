"""P2 — classificação unificada: modelo, mapa de tipos, gate de roteamento."""

import pytest

from backend.app.models.document import DocumentType
from backend.app.services.document_classification import (
    ClassificationResult,
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
