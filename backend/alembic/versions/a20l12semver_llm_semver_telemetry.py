"""A20.l12: prompt_version semver puro + confidence/needs_review em llm_call_log.

Revision ID: a20l12semver
Revises: adr173budgetnull
Create Date: 2026-07-02

Errata ADR-233 §Migration: valores legados ``<slug>-v<semver>`` viram semver
puro; o original é preservado em ``prompt_version_legacy`` (auditoria — o
snapshot CSV do runbook usa esta coluna). ADR-260: ``confidence`` +
``needs_review`` viram colunas SQL para análise por prompt_version sem
depender do OTLP (A20.l13).
"""

import re
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import context, op

revision: str = "a20l12semver"
down_revision: Union[str, Sequence[str], None] = "adr173budgetnull"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_LEGACY_RE = re.compile(r"^([\w-]+)-v(\d+\.\d+\.\d+)$")


def upgrade() -> None:
    op.add_column("llm_call_log", sa.Column("prompt_version_legacy", sa.Text(), nullable=True))
    op.add_column("llm_call_log", sa.Column("confidence", sa.Float(), nullable=True))
    op.add_column(
        "llm_call_log",
        sa.Column("needs_review", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # Data migration em Python — regex portátil (SQLite dev + Postgres prod);
    # tabela é telemetria (volume baixo), full scan aceitável. Em ``--sql``
    # (offline) só o DDL é emitido — o remap roda no upgrade online.
    if context.is_offline_mode():
        return
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, prompt_version FROM llm_call_log "
            "WHERE prompt_version IS NOT NULL AND prompt_version LIKE '%-v%'"
        )
    ).fetchall()
    for row_id, legacy in rows:
        match = _LEGACY_RE.match(legacy or "")
        if match is None:
            continue
        conn.execute(
            sa.text(
                "UPDATE llm_call_log SET prompt_version = :new, prompt_version_legacy = :old "
                "WHERE id = :id"
            ),
            {"new": match.group(2), "old": legacy, "id": row_id},
        )


def downgrade() -> None:
    if not context.is_offline_mode():
        conn = op.get_bind()
        conn.execute(
            sa.text(
                "UPDATE llm_call_log SET prompt_version = prompt_version_legacy "
                "WHERE prompt_version_legacy IS NOT NULL"
            )
        )
    op.drop_column("llm_call_log", "needs_review")
    op.drop_column("llm_call_log", "confidence")
    op.drop_column("llm_call_log", "prompt_version_legacy")
