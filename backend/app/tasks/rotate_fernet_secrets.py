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
import os
from datetime import datetime, timezone

from sqlalchemy import select

from backend.app.core.database import SyncSessionLocal
from backend.app.models import (
    FamilyMember,
    LLMConfig,
    PasswordVault,
    PipelineArtifact,
    Protection,
)
from backend.app.services.security.crypto import (
    _key_id,
    decrypt_artifact_payload,
    encrypt_artifact_payload,
    is_encrypted_payload,
)
from backend.app.services.security.vault import get_vault
from backend.app.worker import celery_app

logger = logging.getLogger(__name__)

_BATCH_SIZE = 100

# Data em que `ENCRYPT_PIPELINE_ARTIFACTS` passou a valer (ADR-231): o último
# write em plaintext do dogfood é 2026-05-20T10:22, o primeiro cifrado é
# 2026-05-20T18:26. Row em plaintext ANTES disto é resíduo histórico e fecha
# para sempre; DEPOIS é drift vivo de config — flag desligada ou writer
# contornando `DBArtifactStore.write`. São modos de falha diferentes, e contar
# os dois juntos faz o gate morrer verde assim que o resíduo é limpo.
_ENCRYPTION_CUTOVER = datetime.fromisoformat(
    os.getenv("MATHOMS_ENCRYPTION_CUTOVER", "2026-05-20T18:26:00+00:00")
)

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


def _created_after_cutover(row) -> bool:
    created = getattr(row, "created_at", None)
    if created is None:
        return False
    return (
        created if created.tzinfo else created.replace(tzinfo=timezone.utc)
    ) > _ENCRYPTION_CUTOVER


# Bucket próprio: dentro de `skipped` a row em plaintext era indistinguível de
# "já está na primária", e foi assim que 418 delas atravessaram o gate G0
# (ADR-231 §Emenda 2026-08-21).
def _count_plaintext(row, counts: dict) -> None:
    """Contabiliza row sem sentinel, separando resíduo histórico de drift vivo."""
    counts["plaintext"] += 1
    if _created_after_cutover(row):
        counts["plaintext_after_cutover"] += 1


def _rotate_artifact_row(row, current_kid: str, counts: dict, dry_run: bool) -> None:
    payload = row.content_json
    if not is_encrypted_payload(payload):
        _count_plaintext(row, counts)
        return
    if payload.get("kid") == current_kid:
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
    counts = {"rotated": 0, "skipped": 0, "failed": 0, "plaintext": 0, "plaintext_after_cutover": 0}
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
