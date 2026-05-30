"""ADR-274: índices compostos para consulta de audit de acesso (LGPD Art.37).

Revision ID: adr274auditidx
Revises: adr272reviewreasons
Create Date: 2026-05-30

Com a auditoria de acesso (l7) gravando 1 linha por GET sensível, ``audit_logs``
vira tabela quente de escrita e o caminho de leitura passa a ser dominado por
duas consultas: "acessos deste workspace, mais recentes primeiro" (titular
exercendo Art.18 / operador investigando) e "acessos deste ator, mais recentes
primeiro" (trilha por usuário). Ambas fazem ``WHERE <col> = ? ORDER BY
created_at DESC`` — sem índice composto, o ``ix_audit_logs_created_at`` sozinho
não cobre o predicado de igualdade e o ``ix_audit_logs_workspace_id`` sozinho
não cobre a ordenação, forçando sort em memória.

Adiciona:
- ``ix_audit_logs_workspace_created`` em ``(workspace_id, created_at)``
- ``ix_audit_logs_actor_created`` em ``(actor_user_id, created_at)``

Remove ``ix_audit_logs_created_at`` (single-col): redundante — o purge diário
(l8) filtra primeiro por ``action IN READ_ACCESS_ACTIONS`` (coberto por
``ix_audit_logs_action``) e qualquer consulta temporal de produto é
workspace- ou actor-scoped (coberta pelos compostos).

Pré-produção: tabela vazia, ``CREATE INDEX`` é instantâneo e não exige
``CONCURRENTLY``. Em escala de produção (tabela grande, append-only quente),
a recriação destes índices deve usar ``CREATE INDEX CONCURRENTLY`` em janela
dedicada — follow-up rastreado na ADR-274 (consequências).
"""

from typing import Sequence, Union

from alembic import op

revision: str = "adr274auditidx"
down_revision: Union[str, Sequence[str], None] = "adr272reviewreasons"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_audit_logs_workspace_created",
        "audit_logs",
        ["workspace_id", "created_at"],
        unique=False,
        postgresql_ops={"created_at": "DESC"},
    )
    op.create_index(
        "ix_audit_logs_actor_created",
        "audit_logs",
        ["actor_user_id", "created_at"],
        unique=False,
        postgresql_ops={"created_at": "DESC"},
    )
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")


def downgrade() -> None:
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.drop_index("ix_audit_logs_actor_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_workspace_created", table_name="audit_logs")
