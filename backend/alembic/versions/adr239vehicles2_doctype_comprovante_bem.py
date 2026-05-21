"""ADR-239 (A18 L1 P3): DocumentType.comprovante_bem.

Revision ID: adr239vehicles2
Revises: adr239vehicles1
Create Date: 2026-05-21

Adiciona valor ``comprovante_bem`` ao enum nativo ``documenttype`` em
Postgres. SQLite armazena ``documenttype`` como TEXT — no-op.

Rationale (ADR-239 D8): comprovantes de bens (CRLV-e em L1; imóveis V2)
têm stage próprio ``extract_comprovantes_bens`` (polimórfico por
``tipo_comprovante``). Distinto de ``other`` porque dispara workflow
de upsert em ``vehicles`` + reconciliação assíncrona com IRPF G02 (P4).

Sem o valor dedicado, CRLV-e cairia em ``DocumentType.other`` e o
classifier perderia roteamento downstream.

Downgrade: Postgres não suporta ``DROP VALUE`` em enum existente.
Política ADR-097 extract-then-refactor (ver migration adr238informes2
para pattern idêntico): ALTER irreversível com pre-down guard contra
rows usando o novo valor.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "adr239vehicles2"
down_revision: Union[str, Sequence[str], None] = "adr239vehicles1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """ALTER TYPE documenttype ADD VALUE em Postgres; no-op em SQLite."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE documenttype ADD VALUE IF NOT EXISTS 'comprovante_bem'")
    # SQLite: documenttype é TEXT livre, aceita qualquer string. No-op.


def downgrade() -> None:
    """Pre-down guard + log explicit; Postgres não suporta DROP VALUE."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        import sqlalchemy as sa

        n = bind.execute(
            sa.text("SELECT COUNT(*) FROM documents WHERE doc_type = 'comprovante_bem'")
        ).scalar()
        if n and int(n) > 0:
            raise RuntimeError(
                f"ADR-239 downgrade bloqueado: {n} document(s) com doc_type="
                f"'comprovante_bem'. UPDATE rows para 'other' antes do downgrade. "
                f"Postgres não permite DROP VALUE em enum existente; este "
                f"downgrade é informativo apenas."
            )
        op.execute(
            "-- ADR-239 downgrade: Postgres não suporta DROP VALUE em documenttype. "
            "Valor 'comprovante_bem' permanece no enum (sem-op)."
        )
    # SQLite: no-op.
