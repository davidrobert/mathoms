---
id: TRACK-a7-3-catalog-override
type: track
title: "Track A7.3 — Catalog + Override resolver (categorization + institutions)"
sprint: A7
status: consumed
created_at: null
consumed_at: null
agent_role: null
tags:
  - type/track
  - sprint/a7
  - status/consumed
---

# Track A7.3 — Catalog + Override resolver (categorization + institutions)

> **Lane ID:** A7.3
> **Branch prefix:** `agent/a7-3-catalog-override/*`
> **Depende de:** A7.1 ✅ mergeada (leitor categorization é via `ConfigStore`).
> **Paralelo com:** — (única lane da Onda 3).
> **Conflita com:** qualquer commit ativo em `backend/app/models/category*.py`, `backend/app/repositories/category*`, `backend/app/api/categories.py`, `backend/app/services/category_resolver.py` (novo), `pipeline/domain/services/categorization_service.py`.
> **Onda:** 3 (serial após A7.1).
> **Plano canônico:** [CONFIG_CUTOVER_PLAN.md §5.3](../CONFIG_CUTOVER_PLAN.md#§53-a73--catalog--override-resolver)
> **ADR:** [ADR-137](../DECISIONS.md#adr-137--catalog--override-resolver-para-categorization-e-institutions) — **G1 obrigatório**.
> **Supervisão CTO:** G1 (ADR) · G2 (schema + migration backfill) · G3 (PR pré-merge).

> **Objetivo (1 frase):** dividir `categorization` em **template global** (taxonomia base do produto) + **overrides por workspace** (apenas diff); `institutions` vira `institution_catalog` global; resolver no read-path; sem materialização redundante.

---

## Por que esta lane

Hoje `categories` table mistura template + customização do cliente. Update do template pelo dev sobrescreve customização do workspace OU customização do workspace bloqueia update do template — drift garantido. Esta lane separa storage explicitamente.

`institutions` é mais simples: vira catalog global; cliente não customiza catálogo (banco fora da lista é ticket de produto).

---

## Regras inegociáveis

1. **Backwards-compatible**: workspaces existentes leem **categorias idênticas** pré e pós cutover. Bench: rodar relatório do workspace piloto, comparar bytes.
2. **`category_templates.key` jamais é renomeado** após publicado (ADR-137). Rename = breaking → exige nova `template_version` + migration de overrides — fora do escopo desta lane.
3. **Cache Redis com invalidação por evento** (ADR-111). Sem `@lru_cache` no resolver.
4. **Frontend não muda contrato API** — endpoints `/v1/workspaces/{id}/categories` continuam retornando `list[ResolvedCategory]`; write passa a criar/atualizar overrides em vez de category rows.
5. **Funções 4-20 linhas, módulos ≤500** (CLAUDE.md §Code style).
6. **Stateless rigoroso** ([ADR-111](../DECISIONS.md)).

---

## Entregáveis (CONFIG_CUTOVER_PLAN.md §5.3)

### Schema (Alembic)

```sql
CREATE TABLE category_templates (
  id UUID PRIMARY KEY,
  key TEXT NOT NULL,
  parent_key TEXT,
  label TEXT NOT NULL,
  default_keywords TEXT[] NOT NULL DEFAULT '{}',
  sort_order INT NOT NULL,
  template_version INT NOT NULL DEFAULT 1,
  UNIQUE (key, template_version)
);

CREATE TABLE workspace_category_overrides (
  id UUID PRIMARY KEY,
  workspace_id UUID NOT NULL REFERENCES workspaces(id),
  template_key TEXT NOT NULL,
  label_override TEXT,
  keywords_override TEXT[],
  disabled BOOLEAN NOT NULL DEFAULT FALSE,
  UNIQUE (workspace_id, template_key)
);

CREATE TABLE institution_catalog (
  id UUID PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  default_parser TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'
);
```

### Migration backfill

1. **Seed `category_templates` v1** a partir de `config/categorization.json` (template_version=1, sort_order monotônico).
2. **Seed `institution_catalog`** a partir de `config/institutions.json`.
3. **Migrar `categories` → overrides**: para cada row em `categories`, comparar com template v1; criar row em `workspace_category_overrides` **apenas** se diverge (label ≠ default ou keywords ≠ default ou alguma coisa custom). Workspaces com 0 customização → 0 rows.

### Backend

4. **Models** + **Repositories** (`category_template_repository.py`, `workspace_category_override_repository.py`, `institution_catalog_repository.py`).

5. **Resolver** (`backend/app/services/category_resolver.py`):
   ```python
   def resolve_categories(workspace_id: UUID, db: Session) -> list[ResolvedCategory]:
       template = load_active_template(db)              # cached Redis
       overrides_by_key = repo.list_overrides(workspace_id, db)
       resolved = []
       for t in template:
           ov = overrides_by_key.get(t.key)
           if ov and ov.disabled:
               continue
           resolved.append(merge(t, ov))
       return resolved
   ```
   `merge()` aplica `label_override`/`keywords_override` quando presentes.

6. **`DBConfigStore.get_categorization`** delega ao resolver (em vez de ler `categories` table direto).

7. **API** (`backend/app/api/categories.py`):
   - `GET /api/v1/workspaces/{id}/categories` continua retornando `list[ResolvedCategory]` — frontend não muda.
   - `POST/PUT/DELETE` — adapta lógica para criar/atualizar `workspace_category_overrides` em vez de `categories`.
   - `GET /api/v1/admin/category-templates` (read-only) — lista template ativo.

8. **Cache Redis** (`backend/app/services/category_resolver.py`):
   - `categories:{workspace_id}:{template_version}` invalidado por evento `category_override.changed` (emitido no use case de write).
   - `category_template:v{N}` cacheado long-lived.

### Pipeline

9. **`pipeline/domain/services/categorization_service.py`** já recebe `CategorizationConfig` em A7.1; nada muda — apenas o adapter (DBConfigStore.get_categorization) passa a usar o resolver.

### Limpeza

10. `git rm config/categorization.json config/institutions.json` no commit final (após smoke verde).

### Testes

11. ≥30 testes novos cobrindo: backfill correto (workspace sem custom → 0 overrides; workspace com custom → overrides corretos), resolver merge correto, disabled funciona, cache invalidação por evento, API contrato estável.

---

## Sequência de commits sugerida

```
1. feat(backend): category_templates + workspace_category_overrides + institution_catalog models + Alembic (A7.3 · ADR-137)
2. feat(backend): backfill data migration from categories + config/categorization.json (A7.3)
3. feat(backend): backfill data migration from config/institutions.json → institution_catalog (A7.3)
4. feat(backend): CategoryTemplateRepository + OverrideRepository + InstitutionCatalogRepository (A7.3)
5. feat(backend): category_resolver + Redis cache + invalidation events (A7.3)
6. refactor(backend): DBConfigStore.get_categorization uses resolver (A7.3)
7. refactor(backend): /v1/.../categories write writes to workspace_category_overrides (A7.3)
8. test(backend): backfill + resolver + cache invalidation (A7.3) — ≥30 tests
9. chore(config): rm config/categorization.json + config/institutions.json (A7.3)
10. docs(a7): A7.3 ✅ + ADR-137 + CHANGELOG
```

---

## Gates de push

```bash
pre-commit run --all-files
pytest backend/tests -q                          # ≥1175 + 30 novos
pytest tests -q                                  # pipeline goldens — categorization tree resolved deve dar bytes idênticos
make smoke                                       # E2E sem JSONs no disco
# bench:
python dev/bench_category_resolve.py --workspace <id>  # p95 < threshold do baseline
```

---

## Acceptance gates (CONFIG_CUTOVER_PLAN.md §5.3)

- [ ] Schema + Alembic + backfill ✓
- [ ] Resolver implementado + cache Redis ✓
- [ ] `DBConfigStore.get_categorization` delega ao resolver ✓
- [ ] API write cria overrides ✓
- [ ] Frontend continua rodando sem mudança ✓
- [ ] Workspaces existentes têm output idêntico pré e pós cutover ✓
- [ ] Bench p95 dentro de ±5% do baseline ✓
- [ ] `categorization.json` + `institutions.json` removidos ✓
- [ ] Smoke E2E verde com JSONs ausentes ✓
- [ ] CTO G1 (ADR-137) ✅ + G2 (schema + backfill) ✅ + G3 (PR review) ✅

---

## O que NÃO entrega

- Override de `institution_catalog` por workspace (ADR-137 §Consequências aceita simplicidade).
- UI de admin para gerenciar template global (fica para F7F-Local).
- Migration para `template_version` 2 (não há v2 ainda).
- Rename de `template_key` (proibido por ADR-137).

---

## Coordenação com outros agentes

- **Onda 3 — única lane.** Roda serialmente após A7.1 mergeada.
- **Hotspots de schema:** Alembic head pode mover entre `git fetch` — rebase obrigatório antes de gerar nova migration.

---

## Rollback

- Revert PR.
- Tabelas novas permanecem (Alembic forward-only).
- API write voltaria a quebrar — risco real. Mitigação: smoke + tests cobrem write paths antes do merge.
- Se rollback for necessário pós-merge, hotfix com revert + restore das tabelas `categories` antigas (ainda existem — esta lane **não dropa** `categories`).

---

## Estimativa

~3 sessões de 2h.
