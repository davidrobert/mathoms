"""ADR-154 M2 — sunset legacy report_collab tables (rename to _legacy_*).

Revision ID: a0b1c2d3e4f5
Revises: f0a1b2c3d4e5
Create Date: 2026-04-29

Direção E · Onda 1 · M2 — sunset (rename + endpoints 410 Gone) das
tabelas legadas `kanban_items` e `report_notes` (ADR-123). Backfill de
dados aconteceu na M1 (f0a1b2c3d4e5); aqui apenas:

1. RENAME `kanban_items` → `_legacy_kanban_items`
2. RENAME `report_notes` → `_legacy_report_notes`

Estratégia conservadora vs DROP direto previsto no ADR-154 §M2:
- Hoje (2026-04-29) é o mesmo dia da M1; janela de 7 dias de validação
  em produção não foi cumprida.
- RENAME é reversível em segundos via downgrade (RENAME inverso).
- DROP é irreversível sem backup.
- Endpoints REST passam a retornar 410 Gone (objetivo principal da M2:
  fechar API surface do legado).
- DROP final fica para PR M3 (sprint+2, ~2026-05-13) após validação.

Modelos SQLAlchemy `KanbanItem` e `ReportNotes` permanecem apontando
para `_legacy_*` (via `__tablename__` atualizado) — necessário porque
`backend/app/services/internal_ops/purge_reports.py` ainda faz DELETE
em ambas tabelas no fluxo de purga de relatórios. Após drop final
(M3), models e DELETE serão removidos.
"""

from __future__ import annotations

from typing import Union

from alembic import op

revision: str = "a0b1c2d3e4f5"
down_revision: Union[str, None] = "f0a1b2c3d4e5"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def upgrade() -> None:
    op.rename_table("kanban_items", "_legacy_kanban_items")
    op.rename_table("report_notes", "_legacy_report_notes")


def downgrade() -> None:
    op.rename_table("_legacy_report_notes", "report_notes")
    op.rename_table("_legacy_kanban_items", "kanban_items")
