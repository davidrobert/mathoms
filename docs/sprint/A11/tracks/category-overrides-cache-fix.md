---
id: TRACK-category-overrides-cache-fix
type: track
title: "Track Category Overrides W1 — Cache invalidation + CategoryOverrideService"
sprint: A11
plan: PLAN-category-overrides-ux
status: consumed
created_at: "2026-05-10"
consumed_at: "2026-05-10"
agent_role: senior-cto
tags:
  - type/track
  - sprint/a11
  - status/consumed
  - area/categorization
  - area/backend
---

# Track Category Overrides W1 — Cache invalidation + `CategoryOverrideService`

> **Lane ID:** category-overrides-cache-fix
> **Plano canônico:** [docs/plan/CATEGORY_OVERRIDES_UX/_README.md](../../../archive/CATEGORY_OVERRIDES_UX_PLAN-2026-05-10.md) §Wave 1
> **Branch prefix:** `agent/category-overrides-cache-fix/*`
> **Depende de:** —
> **Bloqueia:** W4-T01 (UI) — `read-after-write` da W4 fica stale sem este fix
> **Paralelo com:** W2-T01, W3-T01 (zero overlap em files)

## Briefing

Bug latente: `WorkspaceCategoryOverrideRepository.upsert/delete` ([backend/app/repositories/workspace_category_override_repository.py](../../../../backend/app/repositories/workspace_category_override_repository.py)) **não invalida** `category_cache` ([backend/app/services/category_cache.py](../../../../backend/app/services/category_cache.py)). TTL é 300s — em prod, edição de override fica stale por até 5 min no E4.

Solução: criar `CategoryOverrideService` (application layer, ADR-097-compliant) que orquestra repo + cache invalidation write-through pós-commit. Repo fica thin.

## Escopo

- Criar `backend/app/application/categorization/category_override_service.py` com:
  - `CategoryOverrideConfig` (value object frozen — `workspace_id`, `template_key`, `label_override`, `keywords_override`, `monthly_cap_brl_cents_override`, `disabled`, `updated_by_user_id?`).
  - Métodos: `upsert(config)`, `disable(workspace_id, template_key)`, `reset(workspace_id, template_key)`.
  - Cada método: chama repo, commit, **invalida cache** (`category_cache.invalidate(workspace_id)`), log estruturado.
- Refatorar `backend/app/api/category_overrides.py` para consumir o service (não mais o repo direto).
- Repo fica responsável só por CRUD; remover lógica de commit do upsert/delete (service comita).

## Critério de aceite

- [ ] `CategoryOverrideService` recebe `CategoryOverrideConfig` (frozen, ADR-097 D3) — não aceita `dict`/`Path`.
- [ ] `upsert/delete/reset` invalidam `category_cache` write-through pós-commit; falha de invalidação loga warning, não falha o write (TTL natural cuida).
- [ ] Teste `backend/tests/integration/test_category_override_cache.py` (novo): upsert via API → leitura via resolver no mesmo workspace vê valor novo em <100ms (sem TTL warm-up).
- [ ] Repository thin (zero `category_cache` import).
- [ ] `pytest backend/tests -q` verde.
- [ ] `pre-commit run --all-files` verde.

## Arquivos esperados

- **Novo:** `backend/app/application/categorization/category_override_service.py`
- **Novo:** `backend/app/application/categorization/__init__.py` (se ainda não existe)
- **Editado:** `backend/app/repositories/workspace_category_override_repository.py` (thin)
- **Editado:** `backend/app/api/category_overrides.py` (consome service)
- **Novo:** `backend/tests/integration/test_category_override_cache.py`

## Testes

```bash
pytest backend/tests/integration/test_category_override_cache.py -q
pytest backend/tests -q
pre-commit run --all-files
```

## Riscos

- **R1** — invalidação write-through pode não cobrir todos os call-sites. E4 ([scripts/e4_categorize.py](../../../../scripts/categorize_transactions.py)) lê resolver direto via `db_config_store.get_categorization()`; auditar que o cache é o único intermediário. Mitigação: teste end-to-end (`/config/category-overrides/{key}` PUT → resolver via Python sync session).
- **R2** — race entre commit e invalidação. Aceito staleness <100ms. SLA forte futura via versioned cache key (não escopo desta task).

## Ligações

- Plano: [PLAN-category-overrides-ux](../../../archive/CATEGORY_OVERRIDES_UX_PLAN-2026-05-10.md)
- ADR canônica: ADR-185 §3 (a publicar em W3 desta lane)
- ADRs relacionadas: [[ADR-097]] (services com value object), [[ADR-137]] (template + override)
