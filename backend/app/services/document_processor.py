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
    """Map E0-route doc_type string to DocumentType enum.

    E0-route (scripts/e0_route.py) generates specific variant codes like
    ``faturaunique``, ``extratocontabrl``, ``cdbdetalhesdi1``, etc. We group
    them by semantic prefix here. Keep in sync with ``_build_doc_type_patterns``.
    """
    if not e0_doc_type:
        return DocumentType.other

    code = e0_doc_type.lower()

    # IRPF / informes de rendimento → fiscal
    if code.startswith("irpf") or code.startswith("informerendimento"):
        return DocumentType.irpf

    # Investimentos: CDBs, carteira, posição, extrato de investimento
    if (
        code.startswith("cdb")
        or code.startswith("investimentos")
        or code.startswith("carteirarenda")
        or code == "extratoinvest"
    ):
        return DocumentType.investment_report

    # Cartão de crédito: fatura* (exceto fatura de aluguel, que não é cartão)
    if code.startswith("fatura"):
        if code.startswith("faturaaluguel"):
            return DocumentType.other
        return DocumentType.credit_card_bill

    # Extratos bancários: extratoconta*, extratopoupanca, etc.
    if code.startswith("extratoconta") or code.startswith("extratopoupanca"):
        return DocumentType.bank_statement

    return DocumentType.other


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


# Classification confidence threshold. Below this, we escalate to LLM.
_CONTENT_CONFIDENCE_THRESHOLD = 0.8
# Below this, even after LLM, we flag the doc for manual review.
_REVIEW_CONFIDENCE_THRESHOLD = 0.7


def classify_document(file_path: Path, base_dir: Path) -> dict:
    """Classify a document by content (regex → LLM fallback).

    Filename is NOT used — bank exports come with arbitrary or wrong names.
    Pipeline:
        1. Extract text preview from the file.
        2. Content regex classifier (backend.app.services.content_classifier).
        3. If confidence < 0.8 and ANTHROPIC_API_KEY is set → LLM fallback.
        4. If still < 0.7 → mark as ``other`` with ``needs_review=true``.

    Returns dict with keys:
        doc_type, bank_code, period, dest_group, routed_path,
        classification_meta, confidence, needs_review.
    """
    from scripts.e0_route import (
        _init_config as route_init_config,
        _extract_file_preview,
        classify_by_llm,
    )
    from backend.app.services.content_classifier import classify_file

    route_init_config(base_dir)

    # -- Layer 1: content-based regex --------------------------------------
    content_result = classify_file(file_path, _extract_file_preview)
    meta: dict = {
        "source": content_result.source,
        "content": content_result.to_dict(),
    }

    best_type = content_result.doc_type
    best_institution = content_result.institution
    best_period = content_result.period
    best_dest_group = content_result.dest_group
    confidence = content_result.confidence

    # -- Layer 2: LLM fallback ---------------------------------------------
    if confidence < _CONTENT_CONFIDENCE_THRESHOLD:
        llm_result = None
        try:
            llm_result = classify_by_llm(file_path)
        except Exception as exc:  # network / parse error — don't crash upload
            meta["llm_error"] = f"{type(exc).__name__}: {str(exc)[:200]}"

        if llm_result:
            meta["llm"] = llm_result
            llm_confidence = float(llm_result.get("confidence", 0.0) or 0.0)
            if llm_confidence > confidence:
                best_type = llm_result.get("doc_type") or best_type
                best_institution = llm_result.get("institution") or best_institution
                best_period = llm_result.get("period") or best_period
                best_dest_group = llm_result.get("dest_group") or best_dest_group
                confidence = llm_confidence
                meta["source"] = "llm_fallback"

    needs_review = confidence < _REVIEW_CONFIDENCE_THRESHOLD
    meta["confidence"] = confidence
    meta["needs_review"] = needs_review

    # If everything failed, return "other" but preserve any partial signals.
    if not best_type:
        return {
            "doc_type": DocumentType.other,
            "bank_code": best_institution,
            "period": best_period,
            "dest_group": None,
            "routed_path": None,
            "classification_meta": meta,
            "confidence": confidence,
            "needs_review": True,
        }

    return {
        "doc_type": _map_doc_type(best_type),
        "bank_code": best_institution,
        "period": best_period,
        "dest_group": best_dest_group,
        "routed_path": None,
        "classification_meta": meta,
        "confidence": confidence,
        "needs_review": needs_review,
    }


def route_to_data_dir(file_path: Path, dest_group: str | None, tenant_root: Path) -> Path | None:
    """Copy a classified document from inbox/ to data/{dest_group}/.

    This mirrors what E0-route does in CLI mode (move from inbox/ to data/).
    In web mode we copy (not move) so the inbox/ original is preserved as the
    canonical stored_path in the Document model.

    Returns the destination path, or None if dest_group is unknown.
    """
    if not dest_group or not file_path.exists():
        return None

    dest_dir = tenant_root / "data" / dest_group
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest_path = dest_dir / file_path.name
    # Avoid overwriting if name collides
    counter = 1
    while dest_path.exists():
        stem = file_path.stem
        ext = file_path.suffix
        dest_path = dest_dir / f"{stem}_{counter}{ext}"
        counter += 1

    import shutil
    shutil.copy2(str(file_path), str(dest_path))
    return dest_path


def process_uploaded_document(
    file_path: Path,
    passwords: list[str],
    config_dir: Path,
    tenant_root: Path | None = None,
) -> dict:
    """Full processing pipeline for a single uploaded document.

    1. If PDF → check encryption → try unlock with vault passwords
    2. Classify via E0-route regex
    3. If JSON → detect E1/E1.5 type
    4. Route classified file from inbox/ to data/{dest_group}/

    Returns dict with: status, doc_type, bank_code, period, classification_meta, error_message.
    """
    ext = file_path.suffix.lower()

    if ext == ".json":
        json_type = _detect_json_type(file_path)
        if json_type:
            # JSON files (E1/E1.5) go to specific dirs
            if tenant_root and json_type == DocumentType.e1_members_json:
                members_dir = tenant_root / "members"
                members_dir.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copy2(str(file_path), str(members_dir / file_path.name))
            elif tenant_root and json_type == DocumentType.e1_5_baseline_json:
                e2_dir = tenant_root / "processed" / "E2_extracts"
                e2_dir.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copy2(str(file_path), str(e2_dir / file_path.name))
            return {
                "status": DocumentStatus.ready,
                "doc_type": json_type,
                "bank_code": None,
                "period": None,
                "classification_meta": {"source": "json_structure", "type": json_type.value},
                "confidence": 1.0,
                "needs_review": False,
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
                "confidence": 0.0,
                "needs_review": True,
                "error_message": "PDF protegido por senha. Nenhuma senha do vault funcionou.",
            }

    project_root = config_dir.parent if config_dir.name == "config" else config_dir
    classification = classify_document(file_path, project_root)

    # Route file from inbox/ to data/{dest_group}/ so pipeline stages find it
    if tenant_root and classification.get("dest_group"):
        routed = route_to_data_dir(file_path, classification["dest_group"], tenant_root)
        classification["routed_path"] = str(routed) if routed else None

    return {
        "status": DocumentStatus.ready,
        "doc_type": classification["doc_type"],
        "bank_code": classification["bank_code"],
        "period": classification["period"],
        "classification_meta": classification["classification_meta"],
        "confidence": classification.get("confidence", 0.0),
        "needs_review": classification.get("needs_review", False),
        "error_message": None,
    }
