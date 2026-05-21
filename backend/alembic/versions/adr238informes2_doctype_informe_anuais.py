"""ADR-238 (A17 L1 P3): DocumentType.informe_rendimentos_anuais.

Revision ID: adr238informes2
Revises: adr238informes1
Create Date: 2026-05-21

Adiciona valor ``informe_rendimentos_anuais`` ao enum nativo ``documenttype``
em Postgres. SQLite armazena ``documenttype`` como TEXT — no-op.

Rationale (ADR-238 D3): informe anual avulso despacha o stage
``extract_informes_anuais`` (polimórfico por ``tipo_informe``), enquanto
``DocumentType.irpf`` continua disparando ``extract_irpf_full``. Antes da
adição, qualquer informe caía em ``DocumentType.irpf`` por colisão de regex
(`code.startswith("informerendimento")` em
``map_e0_doc_type_to_document_type``) — bug silencioso que processava
informes como declaração e quebrava o pipeline downstream.

Downgrade: Postgres não suporta ``DROP VALUE`` em enum existente. Política
ADR-097 extract-then-refactor: ALTER irreversível, com pre-down guard
contra rows usando o novo valor. Em prod, rollback exige UPDATE rows →
``other`` antes do downgrade.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "adr238informes2"
down_revision: Union[str, Sequence[str], None] = "adr238informes1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """ALTER TYPE documenttype ADD VALUE em Postgres; no-op em SQLite."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # ADD VALUE IF NOT EXISTS é idempotente — re-rodar é seguro.
        op.execute("ALTER TYPE documenttype ADD VALUE IF NOT EXISTS 'informe_rendimentos_anuais'")
    # SQLite: documenttype é TEXT livre, aceita qualquer string. No-op.


def downgrade() -> None:
    """Pre-down guard + log explicit; Postgres não suporta DROP VALUE."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        import sqlalchemy as sa

        n = bind.execute(
            sa.text("SELECT COUNT(*) FROM documents WHERE doc_type = 'informe_rendimentos_anuais'")
        ).scalar()
        if n and int(n) > 0:
            raise RuntimeError(
                f"ADR-238 downgrade bloqueado: {n} document(s) com doc_type="
                f"'informe_rendimentos_anuais'. UPDATE rows para 'other' antes "
                f"do downgrade. Postgres não permite DROP VALUE em enum existente; "
                f"este downgrade é informativo apenas."
            )
        # Mesmo sem rows, Postgres não permite DROP VALUE — log explícito.
        op.execute(
            "-- ADR-238 downgrade: Postgres não suporta DROP VALUE em documenttype. "
            "Valor 'informe_rendimentos_anuais' permanece no enum (sem-op)."
        )
    # SQLite: no-op (TEXT livre).
