"""ADR-214 — CHECK constraint canonical em decisions.code (^D\\d+$).

Revision ID: adr214checkcode
Revises: adr212drop9
Create Date: 2026-05-15

ADR-214: formaliza a convenção implícita ``code ~ '^D\\d+$'`` que a query
de ``DecisionRepository.next_code`` (auto-gen server-side, mesma ADR)
depende para parsear ``substring(code FROM 2)`` em Postgres puro. Em SQLite
(testes) o parse é feito em Python; aqui registramos a constraint apenas
em Postgres porque SQLite não suporta operador regex ``~``.

**Portabilidade:**
- Postgres: ``CHECK (code ~ '^D\\d+$')`` via ``op.create_check_constraint``.
- SQLite (test): noop — fallback Python no repo cobre a invariante.

**Audit pré-deploy** (data-engineer P0): ``SELECT workspace_id, code FROM
decisions WHERE code !~ '^D\\d+$'`` deve retornar 0 rows antes do merge.
Se aparecer, decisão case-a-case (rename ou exclude via WHERE em índice
parcial). Em CI esperamos zero — único cliente é o frontend que sempre
gerou ``D\\d{1,3}``.
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "adr214checkcode"
down_revision: str | None = "adr212drop9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dialect = op.get_context().dialect.name
    if dialect == "postgresql":
        op.create_check_constraint(
            "chk_decisions_code_canonical",
            "decisions",
            "code ~ '^D[0-9]+$'",
        )


def downgrade() -> None:
    dialect = op.get_context().dialect.name
    if dialect == "postgresql":
        op.drop_constraint(
            "chk_decisions_code_canonical",
            "decisions",
            type_="check",
        )
