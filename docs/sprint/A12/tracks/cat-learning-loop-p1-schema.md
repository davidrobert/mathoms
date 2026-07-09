---
id: TRACK-cat-learning-loop-p1-schema
type: track
title: "Track Cat Learning Loop P1 — Schema (transaction_overrides.source + categorization_rules)"
sprint: A12
plan: PLAN-cat-learning-loop
status: ready
created_at: "2026-05-10"
consumed_at: null
agent_role: data-engineer
tags:
  - type/track
  - sprint/a12
  - status/ready
  - area/categorization
  - area/db
---

# Track Cat Learning Loop P1 — Schema base

> **Lane:** [[A12.cat-learning-loop]] · **Plano canônico:**
> [PLAN-cat-learning-loop](../../../archive/CAT_LEARNING_LOOP-2026-07-08.md) §P1
> · **ADR canônica:** [[ADR-186]] §D3
> · **Branch prefix:** `agent/cat-learning-loop-p1-schema/*`
> · **Pré-requisito externo:** [[ADR-187]] (mês fechado · A11.report-publication)
>   shipped em `main` (PR #185, commit `182308a`).
> · **Bloqueia:** P2 (Pipeline E4) — adapter lê tabela criada aqui.

## Briefing

Schema base para o learning loop de categorização ([[ADR-186]] §D3).
**P1 não introduz comportamento novo no pipeline** — apenas tabelas e
modelos. Workspace sem regras promovidas → tabela vazia → goldens E4
inalterados (gate de paridade).

Três mudanças em uma única revision Alembic
(`e7f8a9b0c1d2_adr186_categorization_rules.py`):

1. `transaction_overrides ADD COLUMN source VARCHAR(20) NOT NULL DEFAULT
   'manual'` — distingue override manual (default) de override criado
   pela aplicação automática de regra (P2). Backfill: `server_default`
   cobre linhas existentes.
2. Tabela nova `categorization_rules` ([[ADR-186]] §D3) — agregado de
   regras aprendidas por workspace. Provenance via
   `origin_override_id` (NULLABLE FK), contadores `applied_count` /
   `revert_count` (telemetria de saúde — D6).
3. `transaction_overrides ADD COLUMN rule_id` (NULLABLE FK para
   `categorization_rules.id`, `ON DELETE SET NULL`) — quando E4 (P2)
   aplica regra, popula este campo.

## Critério de aceite (do plano §P1)

- [x] Migration Alembic up/down idempotente (`pytest backend/tests/test_alembic.py -q`).
- [x] Models SQLAlchemy: `CategorizationRule` novo + `TransactionOverride`
      editado (campos `source`, `rule_id`).
- [x] Repository thin: `CategorizationRuleRepository` (`get_by_id`,
      `list_for_workspace`, `create`, `disable`, `bump_applied_count`,
      `bump_revert_count`).
- [x] Pydantic DTOs: `CategorizationRuleCreate`, `CategorizationRuleResponse`.
- [ ] Paridade fixture existente: `pytest backend/tests -q` verde.
- [ ] Goldens E4 inalterados: `pytest tests -q` verde (workspace sem regras).
- [ ] `dev/build_db_schema_reference.py` rodado.
- [ ] `pre-commit run --all-files` verde.

## Arquivos esperados

- **Novo:** `backend/alembic/versions/e7f8a9b0c1d2_adr186_categorization_rules.py`
- **Novo:** `backend/app/models/categorization_rule.py`
- **Editado:** `backend/app/models/transaction_override.py` (+ `source`, `rule_id`)
- **Editado:** `backend/app/models/__init__.py` (export do novo model)
- **Novo:** `backend/app/repositories/categorization_rule_repository.py`
- **Novo:** `backend/app/schemas/dto/categorization_rule/__init__.py`
- **Novo:** `backend/app/schemas/dto/categorization_rule/command.py`
- **Novo:** `backend/app/schemas/dto/categorization_rule/response.py`
- **Editado:** `docs/reference/DB_SCHEMA_REFERENCE.md` (auto-gerado)

## Decisões tomadas

- **1 revision única** para os 3 changes (em vez de 3 separadas) — atômico,
  schema reference fica limpo, single rollback se algo der errado em
  staging.
- **`server_default` em vez de UPDATE explícito** para backfill de
  `transaction_overrides.source` — Alembic SQLite-friendly via batch_alter_table.
- **Sort de `list_for_workspace` em Python** em vez de SQL — SQLite não
  tem `LENGTH()` portável em ORDER BY com expressão composta; lista por
  workspace tem N≤200 (hard cap em P3), custo desprezível.
- **`UniqueConstraint(workspace_id, keyword, target_category)`** em vez
  de partial unique enabled-only — permite "regra desativada de iFood"
  conviver com regra nova; tiebreaker fica em `enabled` filtrado no
  read-path.
- **Sem `unaccent` na keyword** — E4 hoje faz match uppercase puro
  (substring); P2 mantém esta semântica. Se mudarmos para acento-insensitive
  no E4, propaga em P2 com mesma transformação.
- **`category_template` key como string em `target_category`** — não FK
  formal porque template usa `(template_version, key)` composto e a regra
  precisa sobreviver bump de versão. Validação semântica fica no service
  P3 (resolver mostra "regra órfã" se key sumir).

## Testes

```bash
cd backend && alembic upgrade head && alembic downgrade -1 && alembic upgrade head
pytest backend/tests/test_alembic.py -q
pytest backend/tests -q
pytest tests -q
pre-commit run --all-files
```

## Riscos

- **R1** — backfill `source='manual'` em workspaces grandes pode ter
  lock window. Mitigação: `server_default` é DDL; SQLite/PostgreSQL
  atualizam metadados sem rewrite full-table. Smoke test com fixture
  pré-existente cobre.
- **R2** — `rule_id` FK self-referente ao `transaction_overrides`
  (origem) + FK reverso de `transaction_overrides.rule_id` →
  `categorization_rules.id` poderia criar ciclo de delete cascade. **Não
  cria:** ambos são `ON DELETE SET NULL`, não `CASCADE`. Linha mestre é
  `workspaces` (CASCADE em ambos).

## Ligações

- Plano: [PLAN-cat-learning-loop](../../../archive/CAT_LEARNING_LOOP-2026-07-08.md) §P1
- ADR canônica: [[ADR-186]] (Proposto) §D3
- Pré-req: [[ADR-187]] shipped (PR #185, commit `182308a`)
- Lane: [[A12.cat-learning-loop]]
- Track P2 (próximo): `cat-learning-loop-p2-pipeline.md` (criado quando P1 mergear)
