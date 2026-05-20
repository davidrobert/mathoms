"""ADR-226 PR4: bank_accounts partial unique index sobre account_number normalizado."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_INDEX_NAME = "uq_bank_account_workspace_inst_num"


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    # Partial unique sobre normalização digits-only de account_number.
    # PostgreSQL aceita expression index com regexp_replace IMMUTABLE.
    # SQLite (testes) não suporta expression index — skipa; UNIQUE in-app cobre.
    if not _is_postgres():
        return
    op.execute(
        text(
            f"CREATE UNIQUE INDEX IF NOT EXISTS {_INDEX_NAME} "
            "ON bank_accounts ("
            "  workspace_id, "
            "  institution_code, "
            "  regexp_replace(account_number, '\\D', '', 'g')"
            ") WHERE account_number IS NOT NULL"
        )
    )


def downgrade() -> None:
    if not _is_postgres():
        return
    op.execute(text(f"DROP INDEX IF EXISTS {_INDEX_NAME}"))
