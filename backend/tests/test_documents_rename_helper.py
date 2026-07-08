"""Unit tests para `resolve_e0_for_rename` (PATCH /documents/{id} rename canônico) — evita "Sem extrato" enganoso quando filename misclassified é reclassificado manualmente."""

from __future__ import annotations

from backend.app.models.document import Document, DocumentType
from backend.app.services.documents.document_canonical_rename import (
    resolve_e0_for_rename as _resolve_e0_for_rename,
)


def _doc(doc_type: DocumentType, stored_path: str) -> Document:
    return Document(
        workspace_id="ws-1",
        original_name=stored_path.rsplit("/", 1)[-1],
        stored_path=stored_path,
        doc_type=doc_type,
        file_size_bytes=1,
    )


def test_extratoconta_renamed_to_investimentosposicao_when_doc_type_changed():
    """Filename `extratoconta` + tipo `investment_report` → `investimentosposicao` (canônico do reverse map; evita bug "Sem extrato")."""
    doc = _doc(
        DocumentType.investment_report,
        "data/financial_statements/itau_extratoconta_2026-0_original.xls",
    )
    e0_dest = _resolve_e0_for_rename(doc)
    assert e0_dest is not None
    e0_code, dest_group = e0_dest
    assert e0_code == "investimentosposicao"
    assert dest_group == "financial_statements"


def test_keeps_existing_e0_when_filename_already_matches_doc_type():
    """`informerendimentos*` continua válido para IRPF — preserva filename, sem churn de path."""
    doc = _doc(
        DocumentType.irpf,
        "data/income_tax_br/receitafederal_informerendimentos_2025-0_original.pdf",
    )
    e0_dest = _resolve_e0_for_rename(doc)
    assert e0_dest is not None
    e0_code, _ = e0_dest
    assert e0_code == "informerendimentos"


def test_extratoconta_kept_when_doc_type_still_bank_statement():
    """Mudou só `bank_code` ou `period` — filename existente segue válido."""
    doc = _doc(
        DocumentType.bank_statement,
        "data/financial_statements/itau_extratoconta_2026-0_original.pdf",
    )
    e0_dest = _resolve_e0_for_rename(doc)
    assert e0_dest is not None
    assert e0_dest[0] == "extratoconta"


def test_other_returns_none():
    """`DocumentType.other` não tem padrão canônico — pula rename."""
    doc = _doc(DocumentType.other, "data/financial_statements/random-0_original.pdf")
    assert _resolve_e0_for_rename(doc) is None


def test_e1_members_json_returns_none():
    doc = _doc(DocumentType.e1_members_json, "members/family-0_original.json")
    assert _resolve_e0_for_rename(doc) is None


def test_unrecognized_filename_uses_canonical():
    """Filename sem token reconhecível + investment_report → canônico."""
    doc = _doc(
        DocumentType.investment_report,
        "data/financial_statements/random_export-0_original.xls",
    )
    e0_dest = _resolve_e0_for_rename(doc)
    assert e0_dest == ("investimentosposicao", "financial_statements")


def test_handles_string_doc_type():
    """SQLAlchemy às vezes devolve string em hot reload — coerção segura."""
    doc = _doc(DocumentType.investment_report, "data/financial_statements/x-0_original.xls")
    doc.doc_type = "investment_report"  # type: ignore[assignment]
    e0_dest = _resolve_e0_for_rename(doc)
    assert e0_dest == ("investimentosposicao", "financial_statements")


def test_handles_bogus_string_doc_type():
    doc = _doc(DocumentType.bank_statement, "data/x.pdf")
    doc.doc_type = "not_a_real_type"  # type: ignore[assignment]
    assert _resolve_e0_for_rename(doc) is None
