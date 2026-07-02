"""Celery task — re-encripta secrets Fernet com a key primária (ADR-171).

Roda durante a janela de rotação (``MATHOMS_FERNET_KEYS=key_nova,key_antiga``):
varre as colunas cifradas em batches, re-encripta o que só decifra com key
antiga e reporta contagens. Idempotente e resumível — valor já na key
primária é skip; plaintext acidental (dev sem vault) é skip; ciphertext
indecifrável é contado como ``failed`` e NUNCA sobrescrito.

Procedure completa: docs/reference/runbooks/fernet_rotation.md.
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from backend.app.core.database import SyncSessionLocal
from backend.app.models import (
    FamilyMember,
    LLMConfig,
    PasswordVault,
    PipelineArtifact,
    Protection,
)
from backend.app.services.crypto import (
    _key_id,
    decrypt_artifact_payload,
    encrypt_artifact_payload,
    is_encrypted_payload,
)
from backend.app.services.vault import get_vault
from backend.app.worker import celery_app

logger = logging.getLogger(__name__)

_BATCH_SIZE = 100

# (model, coluna ciphertext) — todo secret Fernet em coluna dedicada.
# pipeline_artifacts.content_json (sentinel ADR-231) tem caminho próprio por kid.
_COLUMN_TARGETS = (
    (FamilyMember, "cpf_encrypted"),
    (LLMConfig, "api_key_encrypted"),
    (PasswordVault, "encrypted_password"),
    (Protection, "policy_ref"),
)


def _iter_batches(session, stmt_for_last_pk):
    """Gera batches paginados por PK; ``stmt_for_last_pk(last_pk)`` monta a query."""
    last_pk = None
    while True:
        rows = session.execute(stmt_for_last_pk(last_pk)).scalars().all()
        if not rows:
            return
        yield rows
        last_pk = rows[-1].id


def _rotate_row_value(row, column: str, vault, counts: dict, dry_run: bool) -> None:
    ciphertext = getattr(row, column)
    if not vault.needs_rotation(ciphertext):
        counts["skipped"] += 1
        return
    plaintext = vault.decrypt(ciphertext)
    if plaintext is None:
        counts["failed"] += 1
        logger.error(
            "fernet rotation: undecryptable value",
            extra={"table": type(row).__tablename__, "column": column, "pk": row.id},
        )
        return
    if not dry_run:
        setattr(row, column, vault.encrypt(plaintext))
    counts["rotated"] += 1


def _rotate_column(session, vault, model, column: str, dry_run: bool) -> dict:
    """Re-encripta 1 coluna em batches por PK. Retorna contagens."""
    counts = {"rotated": 0, "skipped": 0, "failed": 0}
    col = getattr(model, column)

    def _stmt(last_pk):
        stmt = select(model).where(col.is_not(None)).order_by(model.id).limit(_BATCH_SIZE)
        return stmt if last_pk is None else stmt.where(model.id > last_pk)

    for rows in _iter_batches(session, _stmt):
        for row in rows:
            _rotate_row_value(row, column, vault, counts, dry_run)
        if not dry_run:
            session.commit()
    return counts


def _rotate_artifact_row(row, current_kid: str, counts: dict, dry_run: bool) -> None:
    payload = row.content_json
    if not is_encrypted_payload(payload) or payload.get("kid") == current_kid:
        counts["skipped"] += 1
        return
    try:
        plaintext_payload = decrypt_artifact_payload(payload)
    except Exception:
        counts["failed"] += 1
        logger.error(
            "fernet rotation: artifact undecryptable",
            extra={"artifact_id": row.id, "kid_stored": payload.get("kid")},
        )
        return
    if not dry_run:
        row.content_json = encrypt_artifact_payload(plaintext_payload)
    counts["rotated"] += 1


def _rotate_artifacts(session, dry_run: bool) -> dict:
    """Re-encripta sentinels ADR-231 cujo ``kid`` difere da key primária."""
    counts = {"rotated": 0, "skipped": 0, "failed": 0}
    current_kid = _key_id()

    def _stmt(last_pk):
        return (
            select(PipelineArtifact)
            .where(PipelineArtifact.id > (last_pk or 0))
            .order_by(PipelineArtifact.id)
            .limit(_BATCH_SIZE)
        )

    for rows in _iter_batches(session, _stmt):
        for row in rows:
            _rotate_artifact_row(row, current_kid, counts, dry_run)
        if not dry_run:
            session.commit()
    return counts


@celery_app.task(name="rotate_fernet_secrets")
def rotate_fernet_secrets(dry_run: bool = False) -> dict:
    """Re-encripta secrets com a key primária (ADR-171); dry_run só conta (runbook §4)."""
    vault = get_vault()
    report: dict = {"dry_run": dry_run, "targets": {}}
    session = SyncSessionLocal()
    try:
        for model, column in _COLUMN_TARGETS:
            key = f"{model.__tablename__}.{column}"
            report["targets"][key] = _rotate_column(session, vault, model, column, dry_run)
        report["targets"]["pipeline_artifacts.content_json"] = _rotate_artifacts(session, dry_run)
    finally:
        session.close()
    total_failed = sum(t["failed"] for t in report["targets"].values())
    log = logger.error if total_failed else logger.info
    log("fernet rotation finished", extra={"report": report})
    return report
