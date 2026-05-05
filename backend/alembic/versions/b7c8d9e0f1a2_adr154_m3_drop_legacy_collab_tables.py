"""ADR-154 M3 — DROP _legacy_kanban_items and _legacy_report_notes.

M2 (2026-04-29) renamed tables to _legacy_*. M3 (2026-05-05) does the final
DROP after 7-day validation window. All data was backfilled to workspace_notes
and tasks tables in M1 (f0a1b2c3d4e5).

Revision ID: b7c8d9e0f1a2
Revises: g3b4c5d6e7f8
Create Date: 2026-05-05
"""

from __future__ import annotations

from typing import Union

from alembic import op

revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "g3b4c5d6e7f8"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def upgrade() -> None:
    op.drop_table("_legacy_kanban_items")
    op.drop_table("_legacy_report_notes")


def downgrade() -> None:
    # Cannot recreate the tables with all their constraints via downgrade —
    # use backup restore if rollback is needed (see docs/runbooks/f9_3_alembic_upgrade.md for pattern).
    raise NotImplementedError(
        "M3 downgrade is not supported — restore from backup taken before M3 upgrade."
    )
