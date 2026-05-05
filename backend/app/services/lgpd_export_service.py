"""LGPD data-export packing — empacota dados do titular em NDJSON tar.gz (Art. 18, V)."""

# Inclui: User (sem hashed_password), Workspaces de membership, e — para
# cada workspace — documents, reports, tasks, decisions, goals, notes,
# suggestions, family_members, categories, pipeline_runs, notifications,
# password_vaults (sem ciphertext), audit_logs, bank_accounts (via
# FamilyMember), workspace_invitations (invited_by ou email). manifest.json
# lista cada `.ndjson` (1 row JSON por linha) com {table, rows, size_bytes}.
# Sync session (worker Celery). Tar.gz é gerado em tmp e movido atômico
# para output_path para evitar arquivos parciais.

from __future__ import annotations

import io
import json
import logging
import os
import tarfile
import tempfile
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models import (
    AuditLog,
    BankAccount,
    Category,
    DataExportRequest,
    Decision,
    Document,
    FamilyMember,
    Goal,
    Notification,
    PasswordVault,
    PipelineRun,
    Report,
    Suggestion,
    Task,
    User,
    Workspace,
    WorkspaceInvitation,
    WorkspaceMember,
    WorkspaceNotes,
)

logger = logging.getLogger(__name__)


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, bytes):
        return f"<bytes:{len(value)}>"
    return value


def _row_to_dict(row: Any, *, exclude: frozenset[str] = frozenset()) -> dict[str, Any]:
    """Serialize SQLAlchemy ORM row to a JSON-safe dict (no relationships)."""
    mapper = inspect(type(row))
    out: dict[str, Any] = {}
    for col in mapper.columns:
        if col.key in exclude:
            continue
        out[col.key] = _to_jsonable(getattr(row, col.key))
    return out


def _user_payload(user: User) -> dict[str, Any]:
    return _row_to_dict(user, exclude=frozenset({"hashed_password"}))


def _vault_payload(row: PasswordVault) -> dict[str, Any]:
    # Encrypted ciphertext is intentionally redacted — LGPD asks for
    # portability of *the user's* data, but the plaintext is encrypted at
    # rest and never decrypted outside the vault read endpoint.
    return _row_to_dict(row, exclude=frozenset({"encrypted_password"}))


def _workspace_member_ids(db: Session, user_id: str) -> list[str]:
    rows = db.execute(
        select(WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == user_id)
    ).all()
    return [r[0] for r in rows]


_WORKSPACE_TABLES: tuple[tuple[str, type], ...] = (
    ("workspace_members", WorkspaceMember),
    ("documents", Document),
    ("reports", Report),
    ("tasks", Task),
    ("decisions", Decision),
    ("goals", Goal),
    ("workspace_notes", WorkspaceNotes),
    ("suggestions", Suggestion),
    ("family_members", FamilyMember),
    ("categories", Category),
    ("pipeline_runs", PipelineRun),
    ("notifications", Notification),
    ("password_vaults", PasswordVault),
    ("audit_logs", AuditLog),
)


def _bank_accounts_for_user(db: Session, workspace_ids: list[str]) -> list[BankAccount]:
    """BankAccount não tem workspace_id direto — junção via FamilyMember."""
    if not workspace_ids:
        return []
    rows = (
        db.execute(
            select(BankAccount)
            .join(FamilyMember, BankAccount.member_id == FamilyMember.id)
            .where(FamilyMember.workspace_id.in_(workspace_ids))
        )
        .scalars()
        .all()
    )
    return list(rows)


def _build_manifest(files: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "format": "ndjson_tar_gz_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "LGPD Art. 18, V — direito à portabilidade",
        "files": files,
    }


def _add_ndjson(
    tar: tarfile.TarFile,
    *,
    name: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows).encode("utf-8")
    if rows:
        payload += b"\n"
    info = tarfile.TarInfo(name=name)
    info.size = len(payload)
    info.mtime = int(datetime.now(timezone.utc).timestamp())
    tar.addfile(info, io.BytesIO(payload))
    return {
        "table": name.removesuffix(".ndjson"),
        "rows": len(rows),
        "size_bytes": len(payload),
    }


def export_user_data(db: Session, *, user_id: str, output_path: Path) -> int:
    """Pack user data → NDJSON tar.gz at ``output_path``; returns size_bytes."""
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if user is None:
        raise ValueError(f"User {user_id} not found")
    workspace_ids = _workspace_member_ids(db, user_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = _new_tmp_path(output_path.parent)
    try:
        with tarfile.open(tmp_path, "w:gz") as tar:
            files_metadata = _pack_all_tables(db, tar, user=user, workspace_ids=workspace_ids)
            _add_manifest(tar, files_metadata)
        os.replace(tmp_path, output_path)
        size = output_path.stat().st_size
        logger.info(
            "lgpd_export.packed user_id=%s workspaces=%d size=%d path=%s",
            user_id,
            len(workspace_ids),
            size,
            output_path,
        )
        return size
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def _new_tmp_path(parent: Path) -> Path:
    with tempfile.NamedTemporaryFile(
        suffix=".tar.gz",
        dir=str(parent),
        delete=False,
    ) as tmp:
        return Path(tmp.name)


def _pack_all_tables(
    db: Session,
    tar: tarfile.TarFile,
    *,
    user: User,
    workspace_ids: list[str],
) -> list[dict[str, Any]]:
    metadata: list[dict[str, Any]] = []
    metadata.append(_add_ndjson(tar, name="user.ndjson", rows=[_user_payload(user)]))
    metadata.append(_pack_workspaces(db, tar, workspace_ids))
    metadata.append(_pack_invitations(db, tar, user))
    metadata.append(_pack_export_history(db, tar, user.id))
    for table_name, model in _WORKSPACE_TABLES:
        metadata.append(_pack_workspace_scoped(db, tar, table_name, model, workspace_ids))
    metadata.append(_pack_bank_accounts(db, tar, workspace_ids))
    return metadata


def _pack_workspaces(db: Session, tar: tarfile.TarFile, workspace_ids: list[str]) -> dict[str, Any]:
    rows = (
        db.execute(select(Workspace).where(Workspace.id.in_(workspace_ids))).scalars().all()
        if workspace_ids
        else []
    )
    return _add_ndjson(tar, name="workspaces.ndjson", rows=[_row_to_dict(w) for w in rows])


def _pack_invitations(db: Session, tar: tarfile.TarFile, user: User) -> dict[str, Any]:
    rows = (
        db.execute(
            select(
                WorkspaceInvitation
            ).where(  # tenancy: global — LGPD export abrange todos os workspaces do usuário
                (WorkspaceInvitation.invited_by == user.id)
                | (WorkspaceInvitation.email == user.email)
            )
        )
        .scalars()
        .all()
    )
    return _add_ndjson(
        tar,
        name="workspace_invitations.ndjson",
        rows=[_row_to_dict(i) for i in rows],
    )


def _pack_export_history(db: Session, tar: tarfile.TarFile, user_id: str) -> dict[str, Any]:
    rows = (
        db.execute(select(DataExportRequest).where(DataExportRequest.user_id == user_id))
        .scalars()
        .all()
    )
    return _add_ndjson(
        tar,
        name="data_export_requests.ndjson",
        rows=[_row_to_dict(r, exclude=frozenset({"download_token"})) for r in rows],
    )


def _pack_workspace_scoped(
    db: Session,
    tar: tarfile.TarFile,
    table_name: str,
    model: type,
    workspace_ids: list[str],
) -> dict[str, Any]:
    if not workspace_ids:
        return _add_ndjson(tar, name=f"{table_name}.ndjson", rows=[])
    rows = db.execute(select(model).where(model.workspace_id.in_(workspace_ids))).scalars().all()
    payloads = (
        [_vault_payload(r) for r in rows]
        if model is PasswordVault
        else [_row_to_dict(r) for r in rows]
    )
    return _add_ndjson(tar, name=f"{table_name}.ndjson", rows=payloads)


def _pack_bank_accounts(
    db: Session, tar: tarfile.TarFile, workspace_ids: list[str]
) -> dict[str, Any]:
    rows = _bank_accounts_for_user(db, workspace_ids)
    return _add_ndjson(tar, name="bank_accounts.ndjson", rows=[_row_to_dict(r) for r in rows])


def _add_manifest(tar: tarfile.TarFile, files_metadata: list[dict[str, Any]]) -> None:
    manifest = _build_manifest(files_metadata)
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
    info = tarfile.TarInfo(name="manifest.json")
    info.size = len(manifest_bytes)
    info.mtime = int(datetime.now(timezone.utc).timestamp())
    tar.addfile(info, io.BytesIO(manifest_bytes))


def export_storage_root() -> Path:
    """Diretório onde os arquivos tar.gz vivem. Fora do storage por-tenant
    para evitar que o cron de purge de workspace apague exports prontos."""
    return settings.STORAGE_ROOT / "lgpd_exports"


def export_path_for(request_id: str) -> Path:
    return export_storage_root() / f"{request_id}.tar.gz"
