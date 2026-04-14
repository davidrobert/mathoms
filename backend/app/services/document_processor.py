"""DocumentProcessor — handles upload processing: unlock PDFs, classify via E0-route."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from backend.app.core.config import settings
from backend.app.models.document import DocumentStatus, DocumentType


def _detect_json_type(file_path: Path) -> Optional[DocumentType]:
    """Detect if a JSON file is an E1 members or E1.5 baseline export."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            if "membros" in data or "members" in data or "family_members" in data:
                return DocumentType.e1_members_json
            if "patrimonio" in data or "baseline" in data or "bens_direitos" in data:
                return DocumentType.e1_5_baseline_json
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, dict):
                if "nome" in first and ("cpf" in first or "nascimento" in first):
                    return DocumentType.e1_members_json
                if "tipo" in first and ("valor" in first or "saldo" in first):
                    return DocumentType.e1_5_baseline_json
    except (json.JSONDecodeError, OSError, KeyError):
        pass
    return None


def _map_doc_type(e0_doc_type: str) -> DocumentType:
    """Map E0-route doc_type string to DocumentType enum."""
    mapping = {
        "extratoconta": DocumentType.bank_statement,
        "extratoinvest": DocumentType.investment_report,
        "faturacartao": DocumentType.credit_card_bill,
        "faturacaratao": DocumentType.credit_card_bill,
        "investimentos": DocumentType.investment_report,
        "cdb": DocumentType.investment_report,
        "irpfdeclaracao": DocumentType.irpf,
        "irpfrecibo": DocumentType.irpf,
        "informerendimentos": DocumentType.irpf,
        "informerendimentosaluguel": DocumentType.irpf,
    }
    return mapping.get(e0_doc_type, DocumentType.other)


def try_unlock_pdf(file_path: Path, passwords: list[str]) -> tuple[bool, bool]:
    """Try to unlock a PDF with the given passwords.

    Returns (is_encrypted, was_unlocked).
    """
    try:
        import pikepdf
    except ImportError:
        return False, False

    try:
        with pikepdf.open(file_path):
            return False, False
    except pikepdf.PasswordError:
        pass
    except Exception:
        return False, False

    for pw in passwords:
        try:
            with pikepdf.open(file_path, password=pw) as pdf:
                tmp = file_path.with_suffix(".tmp.pdf")
                pdf.save(tmp)
            bak = file_path.with_suffix(".bak.pdf")
            try:
                file_path.rename(bak)
                tmp.rename(file_path)
                with pikepdf.open(file_path):
                    pass
                bak.unlink()
            except Exception:
                if bak.exists():
                    if file_path.exists():
                        file_path.unlink()
                    bak.rename(file_path)
                if tmp.exists():
                    tmp.unlink()
                return True, False
            return True, True
        except pikepdf.PasswordError:
            continue
        except Exception:
            return True, False

    return True, False


def classify_document(file_path: Path, base_dir: Path) -> dict:
    """Classify a document using E0-route's regex engine.

    Returns dict with: doc_type, bank_code, period, dest_group, classification_meta.
    Does NOT use LLM (that's Phase 4).
    """
    from scripts.e0_route import (
        _init_config as route_init_config,
        classify_by_name,
    )
    route_init_config(base_dir)

    result = classify_by_name(file_path.name)
    if result is None:
        return {
            "doc_type": DocumentType.other,
            "bank_code": None,
            "period": None,
            "dest_group": None,
            "classification_meta": {"source": "unidentified"},
        }

    return {
        "doc_type": _map_doc_type(result.get("doc_type", "")),
        "bank_code": result.get("institution"),
        "period": result.get("period"),
        "dest_group": result.get("dest_group"),
        "classification_meta": result,
    }


def process_uploaded_document(
    file_path: Path,
    passwords: list[str],
    config_dir: Path,
) -> dict:
    """Full processing pipeline for a single uploaded document.

    1. If PDF → check encryption → try unlock with vault passwords
    2. Classify via E0-route regex
    3. If JSON → detect E1/E1.5 type

    Returns dict with: status, doc_type, bank_code, period, classification_meta, error_message.
    """
    ext = file_path.suffix.lower()

    if ext == ".json":
        json_type = _detect_json_type(file_path)
        if json_type:
            return {
                "status": DocumentStatus.ready,
                "doc_type": json_type,
                "bank_code": None,
                "period": None,
                "classification_meta": {"source": "json_structure", "type": json_type.value},
                "error_message": None,
            }

    if ext == ".pdf" and passwords:
        is_encrypted, was_unlocked = try_unlock_pdf(file_path, passwords)
        if is_encrypted and not was_unlocked:
            return {
                "status": DocumentStatus.needs_password,
                "doc_type": None,
                "bank_code": None,
                "period": None,
                "classification_meta": {"encrypted": True, "unlock_attempted": True},
                "error_message": "PDF protegido por senha. Nenhuma senha do vault funcionou.",
            }

    project_root = config_dir.parent if config_dir.name == "config" else config_dir
    classification = classify_document(file_path, project_root)

    return {
        "status": DocumentStatus.ready,
        "doc_type": classification["doc_type"],
        "bank_code": classification["bank_code"],
        "period": classification["period"],
        "classification_meta": classification["classification_meta"],
        "error_message": None,
    }
