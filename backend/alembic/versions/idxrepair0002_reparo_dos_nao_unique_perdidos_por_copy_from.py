"""Reparo dos 30 índices não-unique perdidos por `copy_from` — paridade com Postgres.

Revision ID: idxrepair0002
Revises: idxrepair0001
Create Date: 2026-08-31

Segunda metade do reparo da [[ADR-423]]. A `idxrepair0001` recriou os 3 UNIQUE que
derrubavam invariante; estes 30 são não-unique e ficaram catalogados aguardando
decisão sobre *se ainda os queremos*.

A medição de 2026-08-31 responde a pergunta e reformula o enunciado: **Postgres já
tem os 30**. Foram criados por migration e sobreviveram lá porque `DefaultImpl` faz
ALTER nativo; só o SQLite os perdeu no drop+recreate. Logo recriá-los não repõe
decisão que ninguém tomou — é o contrário: prod paga o custo de write deles hoje, e
manter o SQLite sem eles é o que sustenta a divergência que já contaminou uma
decisão de desenho (`db_property_supersession_writer`, ADR-423 §Contexto).

Reavaliar se `tasks` precisa de 9 índices continua legítimo — mas é pergunta sobre
**produção**, exige `DROP INDEX CONCURRENTLY` e não cabe num reparo de paridade.
Fica como follow-up nomeado na [[A40.l97]].

Fora deste reparo, por medição e não por omissão:

- **4 são rename, não ausência.** O DB tem o mesmo índice (mesmas colunas, sem
  predicado) sob outro nome, porque a migration nomeou explicitamente e o model
  usa o nome automático de `index=True`. Recriá-los criaria índice duplicado.
  Corrigidos alinhando o *model* ao nome que prod já tem — zero DDL:
  `ix_suggestions_workspace_id`, `ix_ws_econ_override_{workspace_id,classe_auvp,effective_from}`.
- **1 é gap real e `copy_from` não é a causa:** `ix_task_suggestions_status` nunca
  foi criado por migration alguma — Postgres também nunca o teve. Todo read-path de
  `TaskSuggestion.status` é workspace-scoped e já usa `ix_suggestions_ws_status`.
  O `index=True` sai do model em vez de virar índice novo.

Idempotente por inspector pela mesma razão da `idxrepair0001`: em Postgres os 30
existem e `create_index` falharia com "already exists".
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op

revision: str = "idxrepair0002"
down_revision: str | None = "idxrepair0001"
branch_labels: None = None
depends_on: None = None

# (tabela, índice, colunas) — todos não-unique e sem predicado (medido).
_INDICES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("bank_accounts", "ix_bank_accounts_member_id", ("member_id",)),
    ("categories", "ix_categories_workspace_id", ("workspace_id",)),
    ("categorization_rules", "ix_categorization_rules_workspace_id", ("workspace_id",)),
    ("protections", "ix_protections_workspace_id", ("workspace_id",)),
    ("protections", "ix_protections_ws_category", ("workspace_id", "category")),
    ("protections", "ix_protections_ws_ends_at", ("workspace_id", "ends_at")),
    ("protections", "ix_protections_ws_status", ("workspace_id", "status")),
    ("report_publications", "ix_report_publications_workspace_id", ("workspace_id",)),
    (
        "report_publications",
        "ix_report_publications_workspace_period",
        ("workspace_id", "period_yyyymm"),
    ),
    ("stage_reviews", "ix_stage_reviews_pipeline_run_id", ("pipeline_run_id",)),
    ("suggestions", "ix_sugagg_workspace_id", ("workspace_id",)),
    ("suggestions", "ix_sugagg_ws_dedup", ("workspace_id", "dedup_key")),
    ("suggestions", "ix_sugagg_ws_section", ("workspace_id", "section_id")),
    ("suggestions", "ix_sugagg_ws_status", ("workspace_id", "status")),
    ("suggestions", "ix_sugagg_ws_thesis", ("workspace_id", "thesis_key")),
    ("tasks", "ix_tasks_category", ("category",)),
    ("tasks", "ix_tasks_deadline_date", ("deadline_date",)),
    ("tasks", "ix_tasks_parent_task_id", ("parent_task_id",)),
    ("tasks", "ix_tasks_priority", ("priority",)),
    ("tasks", "ix_tasks_status", ("status",)),
    ("tasks", "ix_tasks_workspace_id", ("workspace_id",)),
    ("tasks", "ix_tasks_ws_board_column", ("workspace_id", "board_column")),
    ("tasks", "ix_tasks_ws_priority_status", ("workspace_id", "priority", "status")),
    ("tasks", "ix_tasks_ws_status_deadline", ("workspace_id", "status", "deadline_date")),
    ("transaction_overrides", "ix_transaction_overrides_transaction_hash", ("transaction_hash",)),
    ("transaction_overrides", "ix_transaction_overrides_workspace_id", ("workspace_id",)),
    (
        "workspace_category_overrides",
        "ix_workspace_category_overrides_template_key",
        ("template_key",),
    ),
    (
        "workspace_category_overrides",
        "ix_workspace_category_overrides_workspace_id",
        ("workspace_id",),
    ),
    (
        "workspace_property_overrides",
        "ix_workspace_property_overrides_workspace_id",
        ("workspace_id",),
    ),
    ("workspaces", "ix_workspaces_deleted_at", ("deleted_at",)),
)


def _ja_existe(inspector, tabela: str, indice: str) -> bool:
    """Idempotência: Postgres JÁ tem estes índices e `create_index` falharia lá."""
    return any(ix["name"] == indice for ix in inspector.get_indexes(tabela))


def upgrade() -> None:
    """Recria os 30, pulando os que já existem."""
    if context.is_offline_mode():
        for tabela, indice, colunas in _INDICES:
            op.create_index(indice, tabela, list(colunas), unique=False)
        return

    inspector = sa.inspect(op.get_bind())
    tabelas = set(inspector.get_table_names())
    for tabela, indice, colunas in _INDICES:
        if tabela in tabelas and not _ja_existe(inspector, tabela, indice):
            op.create_index(indice, tabela, list(colunas), unique=False)


def downgrade() -> None:
    """No-op declarado, pela mesma razão da `idxrepair0001`.

    Nada se perde na ida — o reparo converge o SQLite para o schema que Postgres
    já tem. Dropar não tem cenário de uso, e entrar em `IRREVERSIBLE_MIGRATIONS`
    degradaria o roundtrip de `test_migrations_are_idempotent` para o ramo parcial.
    """
