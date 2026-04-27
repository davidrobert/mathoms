"""ADR-146: bank_accounts.source_tier nullable column + heads merge (A7.6).

Revision ID: z4a5b6c7d8e9
Revises: x2y3z4a5b6c7, y3z4a5b6c7d8
Create Date: 2026-04-27

ADR-146 (rules-as-code A7.6): adiciona coluna ``source_tier`` em
``bank_accounts`` para permitir override workspace-específico da
hierarquia universal de fontes de reconciliação E3.

NULL = usar default Mathoms (mapeado por tipo de fonte / parser do
banco). Não-NULL = override per-account quando o cliente tem razão para
confiar mais ou menos numa fonte específica.

Backwards-compat (ADR-097 estratégia "extract then refactor"):
- add nullable + default None — não popula nem flippa neste PR.
- Lógica de tier-aware dedup vai ser ativada num PR futuro quando
  ``ResolvedBankAccount.tier(workspace_id, db)`` for plumbado em
  ``ReconciliationService.is_duplicate``. Hoje todos os bank_accounts
  ficam com NULL → resolver usa default Mathoms.

Heads merge incidental
======================
A7.2a (decisions, ``x2y3z4a5b6c7``) e A7.2b (fiscal_parameters /
market_rates, originalmente ``x2y3z4a5b6c7`` → renomeado para
``x2adr135fp01`` nesta lane). Antes desta lane existiam dois alembic
heads paralelos: ``x2y3z4a5b6c7`` (decisions) e ``y3z4a5b6c7d8``
(fiscal seed). Esta migration colapsa via tupla em ``down_revision``.
Não introduz schema change adicional além da nova coluna ``source_tier``.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "z4a5b6c7d8e9"
down_revision: Union[str, Sequence[str], None] = ("x2y3z4a5b6c7", "y3z4a5b6c7d8")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable ``source_tier`` column to ``bank_accounts``.

    Tier semantics (per ADR-146):
      1 = Extração LLM de extrato OFX/PDF estruturado (mais confiável)
      2 = Extrato bancário parseado por regex
      3 = Fatura de cartão de crédito
      4 = Screenshot de app extraído por LLM
      5 = Declaração editorial / dedução IRPF / planilha manual

    NULL = use Mathoms default (resolved at runtime from
    ``account_type`` + ``institution.parser``).
    """
    with op.batch_alter_table("bank_accounts") as batch:
        batch.add_column(
            sa.Column(
                "source_tier",
                sa.SmallInteger(),
                nullable=True,
                server_default=None,
            )
        )


def downgrade() -> None:
    """Drop ``source_tier`` column. Workspace overrides are lost."""
    with op.batch_alter_table("bank_accounts") as batch:
        batch.drop_column("source_tier")
