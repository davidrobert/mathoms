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


def _rotate_column(session, vault, model, column: str, dry_run: bool) -> dict:
    """Re-encripta 1 coluna em batches por PK. Retorna contagens."""
    counts = {"rotated": 0, "skipped": 0, "failed": 0}
    col = getattr(model, column)
    last_pk = None
    while True:
        stmt = select(model).where(col.is_not(None)).order_by(model.id).limit(_BATCH_SIZE)
        if last_pk is not None:
            stmt = stmt.where(model.id > last_pk)
        rows = session.execute(stmt).scalars().all()
        if not rows:
            break
        for row in rows:
            last_pk = row.id
            ciphertext = getattr(row, column)
            if not vault.needs_rotation(ciphertext):
                counts["skipped"] += 1
                continue
            plaintext = vault.decrypt(ciphertext)
            if plaintext is None:
                counts["failed"] += 1
                logger.error(
                    "fernet rotation: undecryptable value",
                    extra={"table": model.__tablename__, "column": column, "pk": row.id},
                )
                continue
            if not dry_run:
                setattr(row, column, vault.encrypt(plaintext))
            counts["rotated"] += 1
        if not dry_run:
            session.commit()
    return counts


def _rotate_artifacts(session, dry_run: bool) -> dict:
    """Re-encripta sentinels ADR-231 cujo ``kid`` difere da key primária."""
    counts = {"rotated": 0, "skipped": 0, "failed": 0}
    current_kid = _key_id()
    last_pk = 0
    while True:
        rows = (
            session.execute(
                select(PipelineArtifact)
                .where(PipelineArtifact.id > last_pk)
                .order_by(PipelineArtifact.id)
                .limit(_BATCH_SIZE)
            )
            .scalars()
            .all()
        )
        if not rows:
            break
        for row in rows:
            last_pk = row.id
            payload = row.content_json
            if not is_encrypted_payload(payload) or payload.get("kid") == current_kid:
                counts["skipped"] += 1
                continue
            try:
                plaintext_payload = decrypt_artifact_payload(payload)
            except Exception:
                counts["failed"] += 1
                logger.error(
                    "fernet rotation: artifact undecryptable",
                    extra={"artifact_id": row.id, "kid_stored": payload.get("kid")},
                )
                continue
            if not dry_run:
                row.content_json = encrypt_artifact_payload(plaintext_payload)
            counts["rotated"] += 1
        if not dry_run:
            session.commit()
    return counts


@celery_app.task(name="rotate_fernet_secrets")
def rotate_fernet_secrets(dry_run: bool = False) -> dict:
    """Re-encripta todos os secrets com a key primária vigente (ADR-171).

    ``dry_run=True`` só conta (nada é escrito) — passo de validação do runbook.
    """
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
