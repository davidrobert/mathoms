"""``family_member_pii_service`` — CPF fora do boundary LLM (ADR-259 §3 · A20.l15).

O LLM emite só ``cpf_present``; o VALOR é extraído por regex do documento
ORIGINAL, associado ao membro por proximidade de nome e cifrado em
``FamilyMember.cpf_encrypted`` via vault Fernet. Também purga CPF cru de
artifacts E1 legados (backfill policy W1α-T01: re-criptografa via este
serviço + purga o payload — nunca re-extração via LLM).
"""

from __future__ import annotations

import copy
import logging
import unicodedata
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.family_member import FamilyMember
from backend.app.services.vault import get_vault
from pipeline.domain.services.informe_member_matcher import extract_document_cpfs

logger = logging.getLogger(__name__)

# Janela de proximidade nome↔CPF no texto (chars). IRPF traz ambos no cabeçalho.
_NAME_WINDOW = 400
_PERSONAL_DIRS = ("income_tax_br",)
_TEXT_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".csv", ".json", ".txt"}


def _fold(text: str) -> str:
    """Lowercase sem acentos — matching de nome robusto a encoding de PDF."""
    normalized = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in normalized if not unicodedata.combining(c)).lower()


def cpf_near_name(text: str, full_name: str) -> Optional[str]:
    """CPF único na janela ao redor do nome; None se ausente/ambíguo."""
    folded_text, folded_name = _fold(text), _fold(full_name)
    if not folded_name:
        return None
    idx = folded_text.find(folded_name)
    if idx < 0:
        return None
    window = text[max(0, idx - _NAME_WINDOW) : idx + len(full_name) + _NAME_WINDOW]
    cpfs = extract_document_cpfs(window)
    return cpfs.pop() if len(cpfs) == 1 else None


def _personal_documents(tenant_root: Path) -> list[Path]:
    """Documentos pessoais do workspace (mesmos dirs do extract_members)."""
    data_dir = tenant_root / "data"
    docs: list[Path] = []
    for sub in _PERSONAL_DIRS:
        d = data_dir / sub
        if d.exists():
            docs.extend(
                f
                for f in sorted(d.rglob("*"))
                if f.is_file() and f.suffix.lower() in _TEXT_EXTENSIONS
            )
    return docs


def _match_cpf_in_documents(docs: list[Path], full_name: str, extractor) -> Optional[str]:
    for doc in docs:
        try:
            text = extractor.extract(doc)
        except Exception:
            continue
        cpf = cpf_near_name(text, full_name)
        if cpf:
            return cpf
    return None


def mask_cpf_last_digits(cpf_plain: str) -> str:
    """Máscara canônica ``***.***.789-00`` (ADR-259 §4) — 3 dígitos do corpo + verificadores."""
    digits = "".join(c for c in cpf_plain if c.isdigit())
    if len(digits) != 11:
        raise ValueError(f"CPF deve ter 11 dígitos, recebido {len(digits)}: {cpf_plain!r}")
    return f"***.***.{digits[6:9]}-{digits[9:11]}"


def _members_without_cpf(db: Session, workspace_id: str) -> list[FamilyMember]:
    stmt = select(FamilyMember).where(
        FamilyMember.workspace_id == workspace_id,
        FamilyMember.cpf_encrypted.is_(None),
    )
    return list(db.execute(stmt).scalars().all())


def _fill_member_cpfs(members, docs, counts: dict, *, dry_run: bool) -> None:
    from pipeline.llm.text_extractor import DocumentTextExtractor

    extractor = DocumentTextExtractor(max_chars=80_000)
    vault = get_vault()
    for member in members:
        cpf = _match_cpf_in_documents(docs, member.full_name, extractor)
        if cpf is None:
            counts["unmatched"] += 1
            continue
        if not dry_run:
            member.cpf_encrypted = vault.encrypt(cpf)
        counts["filled"] += 1


def backfill_member_cpfs(
    db: Session, *, workspace_id: str, tenant_root: Path, dry_run: bool = True
) -> dict:
    """Preenche ``cpf_encrypted`` NULL dos documentos originais; idempotente (nunca sobrescreve), ``dry_run=True`` só conta."""
    members = _members_without_cpf(db, workspace_id)
    counts = {"dry_run": dry_run, "candidates": len(members), "filled": 0, "unmatched": 0}
    docs = _personal_documents(Path(tenant_root)) if members else []
    if members and not docs:
        counts["unmatched"] = len(members)
        return counts
    _fill_member_cpfs(members, docs, counts, dry_run=dry_run)
    if not dry_run:
        db.commit()
    logger.info("family_member_pii backfill", extra={"workspace_id": workspace_id, **counts})
    return counts


def _e1_member_rows(db: Session, workspace_id: str) -> list:
    from backend.app.models.pipeline_artifact import PipelineArtifact

    stmt = select(PipelineArtifact).where(
        PipelineArtifact.workspace_id == workspace_id,
        PipelineArtifact.stage.in_(("E1", "extract_members")),
        PipelineArtifact.artifact_key == "members",
    )
    return list(db.execute(stmt).scalars().all())


def _strip_cpf_from_membros(payload: dict) -> bool:
    """Troca ``cpf`` cru por ``cpf_present: true`` — preserva o sinal, elimina o valor."""
    changed = False
    for info in (payload.get("membros") or {}).values():
        if isinstance(info, dict) and info.pop("cpf", None) is not None:
            info["cpf_present"] = True
            changed = True
    return changed


def _purge_row(row, *, dry_run: bool) -> bool:
    from backend.app.services.crypto import (
        encrypt_artifact_payload,
        is_encrypted_payload,
        read_artifact_content,
    )

    was_encrypted = is_encrypted_payload(row.content_json)
    # Cópia profunda: mutação in-place no dict da coluna JSON não marca a
    # row como dirty no SQLAlchemy — o UPDATE nunca aconteceria.
    payload = copy.deepcopy(read_artifact_content(row.content_json))
    if not isinstance(payload, dict) or not _strip_cpf_from_membros(payload):
        return False
    if not dry_run:
        row.content_json = encrypt_artifact_payload(payload) if was_encrypted else payload
    return True


def purge_cpf_from_e1_artifacts(db: Session, *, workspace_id: str, dry_run: bool = True) -> dict:
    """Remove ``membros.*.cpf`` cru de artifacts E1 legados (política W1α-T01)."""
    rows = _e1_member_rows(db, workspace_id)
    counts = {"dry_run": dry_run, "scanned": len(rows), "purged": 0}
    counts["purged"] = sum(1 for row in rows if _purge_row(row, dry_run=dry_run))
    if not dry_run:
        db.commit()
    logger.info("e1 artifact cpf purge", extra={"workspace_id": workspace_id, **counts})
    return counts
