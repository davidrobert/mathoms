"""DocumentProcessor — handles upload processing: unlock PDFs, classify via E0-route."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from backend.app.core.config import settings
from backend.app.models.document import DocumentStatus, DocumentType
from backend.app.services.canonical_routing import (
    ensure_minus_zero_original_filename,
    route_inbox_to_canonical_data,
)
from backend.app.services.classification_telemetry import emit_classification_outcome
from backend.app.services.document_classification import (
    classification_can_route_to_data,
    classify_document,
)


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


def resolve_classification_base(config_dir: Path, tenant_root: Path | None) -> Path:
    """Directory whose ``config/`` subtree is used by ``scripts.route_documents._init_config``.

    Prefer the tenant workspace when pipeline config has been materialized there
    (``tenant_root/config/institutions.json``), so LLM prompts and ``family_members``
    match the workspace. Otherwise use the global project root derived from
    *config_dir* (typically ``settings.PIPELINE_ROOT``).
    """
    global_root = config_dir.parent if config_dir.name == "config" else config_dir
    if tenant_root is not None:
        t = tenant_root.resolve()
        if (t / "config" / "institutions.json").is_file():
            return t
    return global_root.resolve()


_JSON_TYPE_DEST_SUBDIR: dict[DocumentType, tuple[str, ...]] = {
    DocumentType.e1_members_json: ("members",),
    DocumentType.e1_5_baseline_json: ("processed", "E2_extracts"),
}


def _copy_json_to_canonical(
    file_path: Path, tenant_root: Path, dest_parts: tuple[str, ...]
) -> str | None:
    """Copia JSON para subdir canônica + renomeia para `*-0_original.json`.
    Retorna caminho relativo ao `tenant_root` (POSIX) ou None em erro.
    """
    import shutil

    dest_dir = tenant_root.joinpath(*dest_parts)
    dest_dir.mkdir(parents=True, exist_ok=True)
    final_name = ensure_minus_zero_original_filename(file_path.name)
    dest = dest_dir / final_name
    shutil.copy2(str(file_path), str(dest))
    try:
        rel = dest.resolve().relative_to(tenant_root.resolve())
        return str(rel).replace("\\", "/")
    except ValueError:
        return None


def _process_json_document(
    file_path: Path,
    *,
    tenant_root: Path | None,
    workspace_id: str | None,
) -> dict | None:
    """Se o arquivo for JSON E1/E1.5 conhecido, copia para subdir canônica e
    retorna payload pronto. Retorna None se não for JSON conhecido."""
    json_type = _detect_json_type(file_path)
    if json_type is None:
        return None
    stored_rel: str | None = None
    dest_parts = _JSON_TYPE_DEST_SUBDIR.get(json_type)
    if tenant_root and dest_parts:
        stored_rel = _copy_json_to_canonical(file_path, tenant_root, dest_parts)
    out = {
        "status": DocumentStatus.ready,
        "doc_type": json_type,
        "bank_code": None,
        "period": None,
        "classification_meta": {"source": "json_structure", "type": json_type.value},
        "confidence": 1.0,
        "needs_review": False,
        "error_message": None,
        "stored_path_relative": stored_rel,
    }
    emit_classification_outcome(
        context="upload",
        classification=out,
        workspace_id=workspace_id,
        outcome="json_structure",
    )
    return out


def _locked_pdf_response(workspace_id: str | None) -> dict:
    """Payload de resposta para PDF protegido por senha não desbloqueado."""
    emit_classification_outcome(
        context="upload",
        classification={
            "doc_type": None,
            "confidence": 0.0,
            "needs_review": True,
            "classification_meta": {"encrypted": True},
        },
        workspace_id=workspace_id,
        outcome="needs_password",
    )
    return {
        "status": DocumentStatus.needs_password,
        "doc_type": None,
        "bank_code": None,
        "period": None,
        "classification_meta": {"encrypted": True, "unlock_attempted": True},
        "confidence": 0.0,
        "needs_review": True,
        "error_message": "PDF protegido por senha. Nenhuma senha do vault funcionou.",
        "stored_path_relative": None,
    }


def _move_and_record_routed(
    file_path: Path,
    classification: dict,
    *,
    tenant_root: Path,
    classification_root: Path,
    content_hash: str | None,
) -> str | None:
    """Executa route_inbox_to_canonical_data e atualiza classification['routed_path']."""
    routed = route_inbox_to_canonical_data(
        file_path,
        tenant_root,
        classification_root,
        dest_group=classification["dest_group"],
        e0_doc_type=classification["e0_doc_type"],
        institution=classification.get("bank_code"),
        period=classification.get("period"),
        classification_meta=classification.get("classification_meta"),
        content_hash=content_hash,
    )
    if not routed:
        classification["routed_path"] = None
        return None
    abs_dest, stored_rel = routed
    classification["routed_path"] = str(abs_dest)
    return stored_rel


def _inbox_rel_path(file_path: Path, tenant_root: Path) -> str | None:
    """Caminho relativo do arquivo ainda no inbox (fallback sem rotear)."""
    try:
        return str(file_path.resolve().relative_to(tenant_root.resolve())).replace("\\", "/")
    except ValueError:
        return None


def _route_classified_file(
    file_path: Path,
    classification: dict,
    *,
    tenant_root: Path | None,
    classification_root: Path,
    content_hash: str | None,
) -> str | None:
    """Se pode rotear (needs_review=False), move inbox → data/; senão fica
    onde está e computa caminho relativo. Mutaciona `classification` com
    `routed_path`. Retorna `stored_path_relative`.

    Só renomeamos quando a classificação é confiante o suficiente. Arquivos
    com baixa confiança (imagens, PDFs sem ANTHROPIC_API_KEY) ficam no
    inbox com o nome original para revisão manual — evita
    `unknown_other_None-0_original.jpg`.
    """
    if not tenant_root:
        return None
    if classification_can_route_to_data(classification):
        return _move_and_record_routed(
            file_path,
            classification,
            tenant_root=tenant_root,
            classification_root=classification_root,
            content_hash=content_hash,
        )
    classification["routed_path"] = None
    return _inbox_rel_path(file_path, tenant_root)


def process_uploaded_document(
    file_path: Path,
    passwords: list[str],
    config_dir: Path,
    tenant_root: Path | None = None,
    workspace_id: str | None = None,
    content_hash: str | None = None,
) -> dict:
    """Full processing pipeline for a single uploaded document.

    1. If PDF → check encryption → try unlock with vault passwords
    2. Classify content-first (same pipeline as E0-route when backend is available)
    3. If JSON → detect E1/E1.5 type
    4. Route classified file from inbox/ to data/{dest_group}/

    When ``content_hash`` is provided it is threaded through to
    ``route_inbox_to_canonical_data`` so the canonical filename gets the
    ``{hash[:12]}_`` prefix (ADR-084). Caller typically supplies the sha256 of
    the pre-unlock bytes (matching ``Document.content_hash``).

    Returns dict with: status, doc_type, bank_code, period, classification_meta, error_message.
    """
    ext = file_path.suffix.lower()

    if ext == ".json":
        json_result = _process_json_document(
            file_path, tenant_root=tenant_root, workspace_id=workspace_id
        )
        if json_result is not None:
            return json_result

    if ext == ".pdf" and passwords:
        is_encrypted, was_unlocked = try_unlock_pdf(file_path, passwords)
        if is_encrypted and not was_unlocked:
            return _locked_pdf_response(workspace_id)

    classification_root = resolve_classification_base(config_dir, tenant_root)
    classification = classify_document(file_path, classification_root)
    stored_rel = _route_classified_file(
        file_path,
        classification,
        tenant_root=tenant_root,
        classification_root=classification_root,
        content_hash=content_hash,
    )

    emit_classification_outcome(
        context="upload",
        classification=classification,
        workspace_id=workspace_id,
        outcome="classified",
    )
    return {
        "status": DocumentStatus.ready,
        "doc_type": classification["doc_type"],
        "bank_code": classification["bank_code"],
        "period": classification["period"],
        "classification_meta": classification["classification_meta"],
        "confidence": classification.get("confidence", 0.0),
        "needs_review": classification.get("needs_review", False),
        "error_message": None,
        "stored_path_relative": stored_rel,
    }
