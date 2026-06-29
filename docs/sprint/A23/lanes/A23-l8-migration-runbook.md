---
id: A23.l8
type: lane
title: "Data Lineage F1 — runbook de migrations + FK DB (G-e)"
sprint: A23
plan: PLAN-data-lineage
status: shipped
priority: P0
branch_slug: dl-f1-migration-runbook
adrs:
  - "[[ADR-278]]"
depends_on:
  - "[[A23.l5]]"
parallel_with: []
tags:
  - type/lane
  - sprint/a23
  - status/in-progress
  - priority/p0
  - area/data-lineage
  - area/persistence
  - area/infra
---

# A23.l8 — runbook de migrations + FK DB (`data_lineage_migrations.md`)

> **Plano:** [[PLAN-data-lineage]] · Onda 1 (F1) · guard-rail **G-e**. Conforma à
> [[ADR-278]] (Decidida) §consequências; não reabre. Co-design `sre-devops` +
> `data-engineer` + `information-architect` registrado em 2026-06-09.

## Objetivo

Consolidar o débito operacional da Onda 1: (1) **materializar o FK DB deferido** da
[[A23.l5]] — `pipeline_artifacts.data_source_id → data_source.id ON DELETE SET NULL`,
Postgres-only; (2) escrever o **runbook G-e** cobrindo as migrations de F1 com janela
PITR + rollback por fase.

## Escopo

| Item | Onde | Status |
|---|---|---|
| Migration FK `adr278datasourcefk` (NOT VALID + VALIDATE; SQLite no-op) | `backend/alembic/versions/adr278fk_data_source_fk.py` | ✅ |
| Teste dedicado (`pytestmark=migration`): offline SQL pg + no-op SQLite | `backend/tests/test_data_source_fk_migration.py` | ✅ |
| Runbook multi-migration (PITR + rollback por fase) | `docs/reference/runbooks/data_lineage_migrations.md` | ✅ |

## Decisões travadas (co-design)

- **NOT VALID + VALIDATE em transações SEPARADAS via `autocommit_block`** (`sre-devops`):
  na mesma transação, o `ADD … NOT VALID` (ACCESS EXCLUSIVE, instantâneo) seguraria o lock
  forte durante todo o scan do `VALIDATE` em `pipeline_artifacts` (alto volume). Separar
  libera o lock antes do scan, que roda sob SHARE UPDATE EXCLUSIVE sem travar escrita.
  CONCURRENTLY **não** se aplica a FK (é p/ índice — documentado como operação futura no
  runbook).
- **Remediação idempotente de órfão embutida antes do `ADD`** (`sre-devops`): workspace
  deletado entre a fase B e este FK pode deixar `data_source_id` apontando para
  `data_source` removido → `VALIDATE` falharia inteiro. `UPDATE … SET NULL` idempotente
  (semântica final do FK) elimina o modo de falha de deploy.
- **Model mantém `data_source_id` plain (sem `ForeignKey`); NÃO tocar
  `KNOWN_PRE_EXISTING_DRIFT`** (`data-engineer`): o `_diff_signature` do
  `test_alembic_guardrails` é **cego a FK** (retorna `None` p/ `add_fk_constraint`) →
  declarar o FK no model não geraria drift, mas catalogar um drift de FK **quebraria** o
  suite via o branch `fixed_drift`. FK é constraint DB-level Postgres-only; integridade
  ORM via app layer (lineage navega em F3+). Constraint **nomeada explicitamente**
  (`fk_pipeline_artifacts_data_source_id`) — o `pg_constraint` check do runbook depende disso.
- **Runbook: template repetido por fase + blockquote de metadados** (`information-architect`):
  localidade sob pressão > DRY (operador não pula para template no topo durante incidente).
  Referencia `disaster_recovery.md` (DR/Fernet) e `f9_3_alembic_upgrade.md` (template) sem
  duplicar. Fase D (cutover futuro) como placeholder `🔜 Futura (A24)`, não executável.
  Migrations existentes → link relativo; futuras → code-span (gate de doc-links).

## Critério de aceite

- `backend/tests/test_data_source_fk_migration.py` (`-m migration`) verde: offline SQL pg
  contém `NOT VALID` + `VALIDATE CONSTRAINT` + `ON DELETE SET NULL` + nome da constraint;
  SQLite no-op (FK ausente, upgrade/downgrade não erram).
- `backend/tests/test_alembic_guardrails.py` verde **sem nova entrada em
  `KNOWN_PRE_EXISTING_DRIFT`** (prova: model plain não gera drift; FK invisível ao signature).
- Single head após `git fetch` pré-push (linearidade).
- `check_doc_links` verde no runbook (wikilinks [[ADR-278]]/[[ADR-282]]/[[PLAN-data-lineage]]
  resolvem; links relativos aos runbooks-irmãos resolvem; migrations futuras em code-span).

## Não-escopo

- `ForeignKey` no model SQLAlchemy → não (FK é DB-level Postgres-only por [[ADR-278]]).
- Enforcement de tenancy via FK composto → não (app-layer; canário no runbook).
- Migrations 2-fases `amount`/`natural_key` (cutover) → A24 (placeholder no runbook).

## Owner sugerido

`sre-devops` (FK NOT VALID/VALIDATE, PITR, rollback) + `data-engineer` (conteúdo/drift) +
`information-architect` (forma do runbook). Co-design da decisão em [[ADR-278]].
