"""Rename pipeline stage identifiers from E* to descriptive names (ADR-093)

Fase 9 do plano unificado (`_scratch/plano_migracao_artifacts_db.md`): renomeia
os valores da coluna ``stage`` em ``pipeline_artifacts`` e ``pipeline_stage_logs``
dos identificadores legados (``"E3"``, ``"E5"``…) para nomes descritivos
(``"reconcile_transactions"``, ``"analyze_finances"``…).

⚠️  **Pré-cutover**: esta migration assume que toda a aplicação já usa o
``STAGE_RENAME_MAP`` como fonte de verdade e que os wrappers/scripts foram
renomeados. Rodá-la antes de ``Fase 9.1-9.2`` quebraria o pipeline em execução.

Procedimento de aplicação (do plano):
  1. Backup obrigatório (``sqlite3 mathoms.db .dump > ...``).
  2. Verificação: nenhum stage desconhecido em ``pipeline_artifacts``.
  3. ``alembic upgrade head``.
  4. Redeploy da app com os novos nomes ativos.

Revision ID: q5r6s7t8u9v0
Revises: p4q5r6s7t8u9
Create Date: 2026-04-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "q5r6s7t8u9v0"
down_revision: Union[str, None] = "p4q5r6s7t8u9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STAGE_RENAME = {
    "E0-audit":    "audit_documents",
    "E0-unlock":   "unlock_documents",
    "E0-route":    "route_documents",
    "E1":          "extract_members",
    "E1.5":        "extract_baseline",
    "E1.5c":       "consolidate_baseline",
    "E2-faturas":  "extract_invoices",
    "E2-extratos": "extract_statements",
    "E2-llm":      "extract_with_llm",
    "E3":          "reconcile_transactions",
    "E4":          "categorize_transactions",
    "E5":          "analyze_finances",
    "E5.N":        "generate_narratives",
    "E6":          "render_report",
    "E7-crossval": "validate_cross",
    "E7-review":   "review_finances",
    "E7-apply":    "apply_review",
    "E6-final":    "render_final_report",
    "E5-revised":  "analyze_finances_revised",
}


def apply_rename(bind, mapping: dict[str, str]) -> None:
    """Aplica ``mapping`` (old→new) em ``pipeline_artifacts`` e ``pipeline_stage_logs``.

    Função extraída para permitir testes sem invocar o CLI do alembic.
    """
    for old, new in mapping.items():
        bind.execute(
            sa.text("UPDATE pipeline_artifacts SET stage = :new WHERE stage = :old"),
            {"old": old, "new": new},
        )
        bind.execute(
            sa.text("UPDATE pipeline_stage_logs SET stage = :new WHERE stage = :old"),
            {"old": old, "new": new},
        )


def upgrade() -> None:
    apply_rename(op.get_bind(), STAGE_RENAME)


def downgrade() -> None:
    reverse = {new: old for old, new in STAGE_RENAME.items()}
    apply_rename(op.get_bind(), reverse)
