"""ADR-236 A16: `BusinessProfile` expandido com 4 chaves (cascata fiscal).

Revision ID: adr236bizprofile1
Revises: adr235nupropriet1
Create Date: 2026-05-21

Sprint A16 (L2 · ADR-236 §D1) — estende o JSON livre em
``Workspace.business_profile_json`` com 4 chaves novas declaradas-pelo-
consultor (não derivam de E3/E4/E1.6):

- ``anexo_simples`` (Literal["III", "V"] | None)
- ``iss_aliquota_pct`` (float 2.0–5.0 | None)
- ``cnae_principal`` (str 'NNNN-N/NN' | None)
- ``tipo_declaracao_ir`` (Literal["completa", "simplificada"] | None)

A coluna ``business_profile_json`` é ``sa.JSON`` (criada em A10.7 via
revision ``b1a2c3d4e5f7``); enforcement de shape é Pydantic-side
(``BusinessProfile`` com ``model_config={"extra": "forbid"}`` em
``backend/app/schemas/business_profile.py``). **Não há DDL** —
upgrade/downgrade são audit-trail puro, refletindo a evolução do
contrato de schema declarativo.

Workspaces existentes não são afetados: chaves novas são opcionais
(default ``None``); ``extra=forbid`` rejeita chaves desconhecidas no
PATCH/GET, mas tolera ausência das novas. Rollback: revisão anterior
``adr235nupropriet1`` aceita o mesmo JSON (Pydantic não enforça do lado
do legado se relaxado).
"""

from typing import Sequence, Union

revision: str = "adr236bizprofile1"
down_revision: Union[str, Sequence[str], None] = "adr235nupropriet1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Sem DDL — schema é Pydantic-side. Esta revision marca o ponto da
    # evolução do contrato em audit trail de migrations.
    pass


def downgrade() -> None:
    # Sem DDL — reverter ADR-236 §D1 exige relaxar o Pydantic na revision
    # anterior, não rodar SQL. Mantido para `alembic downgrade -1` ser
    # reversível.
    pass
