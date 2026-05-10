---
id: TRACK-category-overrides-schema-delta
type: track
title: "Track Category Overrides W2 — Schema delta (updated_by_user_id + DTO version fields)"
sprint: A11
plan: PLAN-category-overrides-ux
status: consumed
created_at: "2026-05-10"
consumed_at: "2026-05-10"
agent_role: data-engineer
tags:
  - type/track
  - sprint/a11
  - status/consumed
  - area/categorization
  - area/db
---

# Track Category Overrides W2 — Schema delta

> **Lane ID:** category-overrides-schema-delta
> **Plano canônico:** [docs/plan/CATEGORY_OVERRIDES_UX/_README.md](../../../plan/CATEGORY_OVERRIDES_UX/_README.md) §Wave 2
> **Branch prefix:** `agent/category-overrides-schema-delta/*`
> **Depende de:** —
> **Bloqueia:** W4-T01 (precisa do DTO `template_version_used`/`latest_template_version` para sinal v2 desatualizada)
> **Paralelo com:** W1-T01, W3-T01 (zero overlap em files)

## Briefing

Adicionar 1 coluna nullable em `workspace_category_overrides` (audit mínima de quem editou) e 2 campos no DTO da resposta do resolver (sinal de v2 desatualizada na UI). Migração não-breaking, sem backfill.

## Escopo

### Migration Alembic

- `workspace_category_overrides.updated_by_user_id`: `String(36)`, FK `users.id`, **nullable**, `on_delete=SET NULL`. Sem default; popula daqui pra frente nos handlers que têm `current_user`.

### DTO

- `ResolvedCategoryDTO` (resposta da API, **não** o domain object `ResolvedCategory`) ganha:
  - `template_version_used: int` — versão do template ativa para a categoria.
  - `latest_template_version: int` — maior `template_version` em `category_templates`.
- Resolver popula ambos a partir de `_get_active_template_version()` ([backend/app/services/category_resolver.py](../../../../backend/app/services/category_resolver.py)).

### Documentação derivada

- Regerar `docs/reference/DB_SCHEMA_REFERENCE.md` via `dev/build_db_schema_reference.py` (auto-gen).
- Regerar `frontend/openapi-snapshot.json` via `make update-openapi-snapshot` (ADR-109).

## Critério de aceite

- [ ] Migration adiciona `updated_by_user_id` (FK `users.id`, nullable, `on_delete=SET NULL`).
- [ ] `ResolvedCategoryDTO` ganha `template_version_used: int` + `latest_template_version: int`.
- [ ] `dev/build_db_schema_reference.py` rodado e diff comitado.
- [ ] `make update-openapi-snapshot` rodado e diff comitado.
- [ ] Migration up + down idempotente (`pytest backend/tests/test_alembic.py -q`).
- [ ] Domain `ResolvedCategory` **não** ganha os campos novos (só DTO de resposta) — separação domínio/contrato preservada.
- [ ] `pre-commit run --all-files` verde.

## Arquivos esperados

- **Novo:** `backend/alembic/versions/<ts>_add_updated_by_to_category_overrides.py`
- **Editado:** `backend/app/models/category_template.py` (campo SQLAlchemy)
- **Editado:** `backend/app/schemas/dto/category.py` (DTO + serializer)
- **Editado:** `backend/app/services/category_resolver.py` (popula DTO)
- **Auto-regerado:** `docs/reference/DB_SCHEMA_REFERENCE.md`, `frontend/openapi-snapshot.json`

## Testes

```bash
pytest backend/tests/test_alembic.py backend/tests/test_openapi_snapshot.py -q
pytest backend/tests -q
pre-commit run --all-files
```

## Riscos

- **R1** — conflito Alembic com lanes em voo (W2-T05 do PLATFORM_REVIEW também migra). **Sempre** rodar `git fetch origin && alembic heads` antes de criar a revision; usar `alembic merge` se necessário.
- **R2** — adicionar campo no DTO mas não no domain pode confundir. Justificativa: `template_version_used` é metadado de "como esta categoria foi resolvida", não pertence à entidade `ResolvedCategory` em si — fica no contrato HTTP.

## Ligações

- Plano: [PLAN-category-overrides-ux](../../../plan/CATEGORY_OVERRIDES_UX/_README.md)
- ADR canônica: ADR-185 §4 (a publicar em W3 desta lane)
- ADRs relacionadas: [[ADR-109]] (OpenAPI snapshot), [[ADR-137]] (template + override)
