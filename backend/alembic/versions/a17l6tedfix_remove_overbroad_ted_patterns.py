"""remove overbroad TED patterns from internal_transfer_patterns (A17.l6)

Revision ID: a17l6tedfix
Revises: adr262memconf
Create Date: 2026-05-23
"""

from __future__ import annotations

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import context, op

revision: str = "a17l6tedfix"
down_revision: Union[str, None] = "adr262memconf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TEMPLATE_VERSION = 1
_METADATA_KEY = "__categorization_metadata__"
_PATTERNS_FIELD = "internal_transfer_patterns"

# Strings removidas — exatamente como estavam no seed v1.
_OVERBROAD_PATTERNS: frozenset[str] = frozenset({"RECEBIMENTO TRANSFERENCIA", "RECEBIMENTO DE TED"})


def _parse_metadata(raw) -> dict:
    if isinstance(raw, str):
        return json.loads(raw) if raw else {}
    return raw if isinstance(raw, dict) else {}


def _load_metadata(bind) -> tuple[str | None, dict]:
    row = bind.execute(
        sa.text(
            "SELECT id, metadata_json FROM category_templates "
            "WHERE template_version = :v AND key = :k"
        ),
        {"v": _TEMPLATE_VERSION, "k": _METADATA_KEY},
    ).fetchone()
    if row is None:
        return None, {}
    return row[0], _parse_metadata(row[1])


def _write_metadata(bind, row_id: str, metadata: dict) -> None:
    """Persiste ``metadata_json`` + ``updated_at`` (now em UTC via DB)."""
    bind.execute(
        sa.text(
            "UPDATE category_templates "
            "SET metadata_json = :m, updated_at = CURRENT_TIMESTAMP "
            "WHERE id = :id"
        ),
        {"m": json.dumps(metadata), "id": row_id},
    )


def upgrade() -> None:
    if context.is_offline_mode():
        # Mutação JSON depende do valor existente — sem bind real em offline.
        # Paridade com o padrão da seed migration `a5b6c7d8e9f0`.
        op.execute(
            "-- A17.l6 internal_transfer_patterns cleanup skipped in offline "
            "mode; run via online migration on target DB."
        )
        return

    bind = op.get_bind()
    row_id, metadata = _load_metadata(bind)
    if row_id is None:
        # Template não foi seedado ainda (deploy novo) — nada a fazer.
        return

    patterns = list(metadata.get(_PATTERNS_FIELD) or [])
    new_patterns = [p for p in patterns if p not in _OVERBROAD_PATTERNS]
    if len(new_patterns) == len(patterns):
        # Strings já ausentes — idempotente.
        return

    metadata[_PATTERNS_FIELD] = new_patterns
    _write_metadata(bind, row_id, metadata)


def downgrade() -> None:
    if context.is_offline_mode():
        op.execute(
            "-- A17.l6 internal_transfer_patterns restore skipped in offline "
            "mode; run via online migration on target DB."
        )
        return

    bind = op.get_bind()
    row_id, metadata = _load_metadata(bind)
    if row_id is None:
        return

    patterns = list(metadata.get(_PATTERNS_FIELD) or [])
    existing = set(patterns)
    to_add = [p for p in _OVERBROAD_PATTERNS if p not in existing]
    if not to_add:
        return

    metadata[_PATTERNS_FIELD] = patterns + to_add
    _write_metadata(bind, row_id, metadata)
