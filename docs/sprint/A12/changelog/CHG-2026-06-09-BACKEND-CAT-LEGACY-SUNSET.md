---
id: CHG-2026-06-09-BACKEND-CAT-LEGACY-SUNSET
type: changelog-entry
date: "2026-06-09"
sprint: A12
lane: "[[A12.cat-legacy-sunset]]"
prs: []
commits: []
summary: |
  backend(a12): sunset do CRUD legado /config/categories em 2 PRs ordenados
  por deploy — PR #573 remove endpoint + use cases + monthly_cap do model;
  PR seguinte dropa a coluna Float via migration. Fecha ADR-283 §B.
breaking: true
tags:
  - type/changelog-entry
  - sprint/a12
  - area/backend
  - area/persistence
  - breaking/api
adrs:
  - "[[ADR-283]]"
  - "[[ADR-137]]"
  - "[[ADR-090]]"
---

# backend(a12): sunset do CRUD legado /config/categories (ADR-283 §B)

Lane **A12.cat-legacy-sunset**, follow-up 1 da [[ADR-283]], em 2 PRs com
ordem obrigatória de deploy (inverter quebraria pods N-1 contra DB migrado):

**PR #573 — código (deploy 1):**

- Endpoint legado `/workspaces/{id}/config/categories` (CRUD, header
  `Deprecation: true` desde A11.W4) removido com os 4 use cases legados,
  `_protocols.py`, `mapper.py` e `CategoryCreateCommand`. OpenAPI −270
  linhas.
- `monthly_cap` (Float, [[ADR-090]] violado) removido do model `Category`,
  do `CategoryRepository.create()` e das factories — o cap canônico segue
  em `workspace_category_overrides.monthly_cap_brl_cents` (cents,
  [[ADR-137]]).
- Caminho moderno intocado: `/config/category-overrides/*`,
  `CategoryUpdateCommand`/`CategoryResponse` (wire), import/export de
  categorization.
- Frontend: funções CRUD mortas, handlers MSW e fixture `categories`
  removidos; mocks migrados para `category-overrides/resolved`.

**PR 2/2 — migration (deploy 2):**

- `f2a3b4c5d6e7` — `DROP COLUMN categories.monthly_cap`
  (`batch_alter_table`, downgrade re-adiciona coluna vazia; perda do dado
  legado documentada e aceita).
- Entrada removida de `MODELS_FLOAT_ALLOWLIST` (`dev/check_float_money.py`)
  e de `KNOWN_PRE_EXISTING_DRIFT` (`test_alembic_guardrails.py`) — gate de
  float monetário em models volta a cobrir `categories` sem exceção.

Breaking: consumidores do CRUD legado recebem 404 (único consumidor —
frontend — migrou em A11.W4).
