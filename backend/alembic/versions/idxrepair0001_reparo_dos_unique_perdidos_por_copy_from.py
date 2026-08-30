"""Reparo dos 3 índices UNIQUE perdidos por `batch_alter_table(copy_from=...)`.

Revision ID: idxrepair0001
Revises: adr417cfs
Create Date: 2026-08-30

`batch_alter_table` sem `recreate=` usa `recreate="auto"`, e
`SQLiteImpl.requires_recreate_in_batch` devolve `True` para qualquer op que não
seja add/create/drop index — ou seja, drop+recreate da tabela. O snapshot passado
em `copy_from=` declara colunas e constraints, mas **não** declara `Index`, então
todo índice nomeado morre no recreate. `DefaultImpl` devolve `False`: em Postgres
as mesmas migrations são ALTER nativo e **nada se perdeu** — o defeito é
SQLite-only (dev, dogfood e a suíte de testes).

Medido em 2026-08-30 contra `head`: **38 índices** declarados no model ausentes no
DB construído por Alembic, em 13 migrations, todas com `copy_from`. Três são
UNIQUE e derrubam invariante de negócio; falsificados por probe comportamental
(inserir a 2ª linha colidente é RECUSADO na revisão anterior e ACEITO em head):

- `workspace_property_overrides.uq_workspace_one_residencia_principal` — 1
  residência principal por workspace. Culpada: `adr235nupropriet1`.
- `report_publications.uq_report_publications_active` — 1 publicação ativa por
  (workspace, período). Culpada: `adr387pr2snap`. É a mais grave: o read-path usa
  `scalar_one_or_none()` sobre `unpublished_at IS NULL`, então duas linhas ativas
  levantam `MultipleResultsFound` dentro de `is_month_closed_sync` — o predicado
  de "mês fechado imutável" ([[ADR-187]]).
- `institution_catalog.ix_institution_catalog_code` — `code` UNIQUE. Culpada:
  `adr238informes1`.

Os ~35 restantes são não-unique (performance) e ficam catalogados como drift
conhecido, com lane própria: o custo de write throughput de 9 índices em `tasks`
nunca foi reavaliado desde a ADR-162, e recriá-los sem decidir seria repor
decisão que ninguém tomou.

Forward-only de propósito. Editar `adr235nupropriet1` in-place não conserta DB já
migrado (precisaria deste reparo de qualquer forma, virando dois mecanismos para
um defeito), e o snapshot `_overrides_table` é compartilhado com o `downgrade()`
de lá — mexer nele muda o caminho de volta também.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op

revision: str = "idxrepair0001"
down_revision: str | None = "adr417cfs"
branch_labels: None = None
depends_on: None = None


# (tabela, índice, colunas, predicado parcial ou None)
_INDICES: tuple[tuple[str, str, tuple[str, ...], str | None], ...] = (
    (
        "workspace_property_overrides",
        "uq_workspace_one_residencia_principal",
        ("workspace_id",),
        "classification = 'residencia_principal'",
    ),
    (
        "report_publications",
        "uq_report_publications_active",
        ("workspace_id", "period_yyyymm"),
        "unpublished_at IS NULL",
    ),
    ("institution_catalog", "ix_institution_catalog_code", ("code",), None),
)

# Colisões que impedem o CREATE UNIQUE. Abortar > deduplicar: escolher *qual*
# linha sobrevive é decisão de domínio, e migration que muta linha em silêncio é
# inauditável. Precedente no próprio repo: o `downgrade` da `adr235nupropriet1`
# levanta `RuntimeError` com o UPDATE a rodar, em vez de resolver sozinho.
_COLISOES: tuple[tuple[str, str], ...] = (
    (
        "workspace_property_overrides",
        "SELECT workspace_id, COUNT(*) FROM workspace_property_overrides "
        "WHERE classification='residencia_principal' "
        "GROUP BY workspace_id HAVING COUNT(*) > 1",
    ),
    (
        "report_publications",
        "SELECT workspace_id, period_yyyymm, COUNT(*) FROM report_publications "
        "WHERE unpublished_at IS NULL "
        "GROUP BY workspace_id, period_yyyymm HAVING COUNT(*) > 1",
    ),
    (
        "institution_catalog",
        "SELECT code, COUNT(*) FROM institution_catalog GROUP BY code HAVING COUNT(*) > 1",
    ),
)


def _abortar_se_ha_colisao(bind: sa.engine.Connection) -> None:
    """Falha alto e acionável antes de qualquer DDL."""
    inspector = sa.inspect(bind)
    existentes = set(inspector.get_table_names())
    for tabela, query in _COLISOES:
        if tabela not in existentes:
            continue
        linhas = bind.execute(sa.text(query)).fetchall()
        if linhas:
            raise RuntimeError(
                f"idxrepair0001 abortada: {tabela} tem {len(linhas)} grupo(s) que violam o "
                f"UNIQUE a recriar. O índice sumiu em SQLite e o dado divergiu desde então.\n"
                f"Inspecione com:\n  {query}\n"
                "Resolva escolhendo qual linha permanece (decisão de domínio, não da "
                "migration) e rode de novo."
            )


def upgrade() -> None:
    """Recria os 3 UNIQUE, pulando os que já existem (Postgres nunca os perdeu)."""
    # Offline (`alembic upgrade --sql`) não reflete schema: `sa.inspect` sobre o
    # MockConnection levanta `NoInspectionAvailable`. Emite o DDL dos três sem
    # pre-check — quem revisa o SQL gerado é humano, e o pre-check roda no apply.
    offline = context.is_offline_mode()
    inspector = None
    tabelas: set[str] = set()
    if not offline:
        bind = op.get_bind()
        _abortar_se_ha_colisao(bind)
        inspector = sa.inspect(bind)
        tabelas = set(inspector.get_table_names())

    for tabela, indice, colunas, predicado in _INDICES:
        if not offline:
            if tabela not in tabelas:
                continue
            # Idempotência não é por causa de DB novo — é porque Postgres JÁ tem
            # estes índices e `op.create_index` puro falharia com "already exists".
            assert inspector is not None
            if any(ix["name"] == indice for ix in inspector.get_indexes(tabela)):
                continue
        kwargs: dict[str, str] = {}
        if predicado is not None:
            kwargs = {"sqlite_where": predicado, "postgresql_where": predicado}
        op.create_index(
            indice,
            tabela,
            list(colunas),
            unique=True,
            **{k: sa.text(v) for k, v in kwargs.items()},
        )


def downgrade() -> None:
    """No-op declarado: o reparo só converge o DB para o que o model sempre disse.

    Dropar índice que restaura invariante é destrutivo e não tem cenário de uso —
    nada foi perdido no caminho de ida. Não entra em `IRREVERSIBLE_MIGRATIONS`
    porque aquele set existe para DROP real, e incluí-lo ali degradaria o
    roundtrip completo de `test_migrations_are_idempotent` para o ramo parcial.
    """
