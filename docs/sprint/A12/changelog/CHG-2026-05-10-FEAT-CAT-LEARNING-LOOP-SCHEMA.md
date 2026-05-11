---
id: CHG-2026-05-10-FEAT-CAT-LEARNING-LOOP-SCHEMA
type: changelog-entry
date: "2026-05-10"
sprint: A12
lane: "[[A12.cat-learning-loop]]"
prs: [188]
commits: ["2a36388"]
summary: |
  feat(db): tabela categorization_rules + transaction_overrides.source/rule_id —
  schema base do learning loop A12.P1.
tags:
  - type/changelog-entry
  - sprint/a12
  - area/categorization
  - area/db
---

# feat(db): schema base do learning loop (A12.P1)

P1 do plano CAT_LEARNING_LOOP entrega o schema que separa override
manual de regra aprendida e habilita auditoria de origem.

**Entregue:**

- Migration: `transaction_overrides ADD COLUMN source VARCHAR(20) NOT
  NULL DEFAULT 'manual'`. Backfill: existentes recebem `'manual'`.
- Tabela `categorization_rules` (ver [[ADR-186]] §D3).
- Coluna `rule_id` em `transaction_overrides` (FK NULL para
  `categorization_rules.id`).
- Models SQLAlchemy + repos.
- Pydantic: `CategorizationRuleCreate`, `CategorizationRuleResponse`.
- Goldens E4 passam inalterados (workspace sem regras = comportamento legado).

Pré-requisito P2 (Pipeline E4).
