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
from backend.app.services.document_classification import (
    classify_document,
    classification_can_route_to_data,
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
    """Directory whose ``config/`` subtree is used by ``scripts.e0_route._init_config``.

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


def process_uploaded_document(
    file_path: Path,
    passwords: list[str],
    config_dir: Path,
    tenant_root: Path | None = None,
) -> dict:
    """Full processing pipeline for a single uploaded document.

    1. If PDF → check encryption → try unlock with vault passwords
    2. Classify content-first (same pipeline as E0-route when backend is available)
    3. If JSON → detect E1/E1.5 type
    4. Route classified file from inbox/ to data/{dest_group}/

    Returns dict with: status, doc_type, bank_code, period, classification_meta, error_message.
    """
    ext = file_path.suffix.lower()

    if ext == ".json":
        json_type = _detect_json_type(file_path)
        if json_type:
            import shutil

            stored_rel: str | None = None  # remains None if tenant_root missing
            # JSON files (E1/E1.5) go to specific dirs — use *-0_original.* for E2/pipeline parity
            if tenant_root and json_type == DocumentType.e1_members_json:
                members_dir = tenant_root / "members"
                members_dir.mkdir(parents=True, exist_ok=True)
                final_name = ensure_minus_zero_original_filename(file_path.name)
                dest = members_dir / final_name
                shutil.copy2(str(file_path), str(dest))
                rel = dest.resolve().relative_to(tenant_root.resolve())
                stored_rel = str(rel).replace("\\", "/")
            elif tenant_root and json_type == DocumentType.e1_5_baseline_json:
                e2_dir = tenant_root / "processed" / "E2_extracts"
                e2_dir.mkdir(parents=True, exist_ok=True)
                final_name = ensure_minus_zero_original_filename(file_path.name)
                dest = e2_dir / final_name
                shutil.copy2(str(file_path), str(dest))
                rel = dest.resolve().relative_to(tenant_root.resolve())
                stored_rel = str(rel).replace("\\", "/")
            return {
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
                "stored_path_relative": None,
            }

    classification_root = resolve_classification_base(config_dir, tenant_root)
    classification = classify_document(file_path, classification_root)

    stored_rel: str | None = None
    # Move inbox → data/... with E0 canonical filename (*-0_original.*).
    #
    # REGRA: só renomeamos/roteamos quando a classificação é confiante o
    # suficiente (needs_review=False). Arquivos com baixa confiança — imagens
    # não identificadas, PDFs somente-imagem sem ANTHROPIC_API_KEY, etc. —
    # ficam no inbox com o nome original para revisão manual na UI.
    #
    # Isso evita nomes como "unknown_other_None-0_original.jpg" que não
    # agregam informação e dificultam a auditoria.
    _can_route = tenant_root and classification_can_route_to_data(classification)
    if _can_route:
        routed = route_inbox_to_canonical_data(
            file_path,
            tenant_root,
            classification_root,
            dest_group=classification["dest_group"],
            e0_doc_type=classification["e0_doc_type"],
            institution=classification.get("bank_code"),
            period=classification.get("period"),
            classification_meta=classification.get("classification_meta"),
        )
        if routed:
            abs_dest, stored_rel = routed
            classification["routed_path"] = str(abs_dest)
        else:
            classification["routed_path"] = None
    elif tenant_root:
        # Arquivo fica onde está (inbox) — computa caminho relativo para o
        # DB (evita caminhos absolutos que quebram ao mover o servidor).
        classification["routed_path"] = None
        try:
            stored_rel = str(
                file_path.resolve().relative_to(tenant_root.resolve())
            ).replace("\\", "/")
        except ValueError:
            stored_rel = None  # fora de tenant_root — ficará como caminho absoluto

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
