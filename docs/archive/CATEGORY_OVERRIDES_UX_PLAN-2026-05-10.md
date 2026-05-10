---
id: PLAN-category-overrides-ux
type: plan
title: Category Overrides UX — V1 (24 default-only)
status: draft
created_at: 2026-05-10
last_review: 2026-05-10
sprint_origem: A11
sprint_atual: A11
sprints_envolvidas: [A11]
paused_at: null
pause_reason: null
adrs_canonical: []
tags:
  - type/plan
  - status/draft
  - area/categorization
  - area/ux
---

# Category Overrides UX — V1 (24 default-only)

> **Origem:** discussão 2026-05-10 entre dono + `product-designer` + `data-engineer` + `product-manager`. Tela atual de configuração de categorias ([frontend/src/app/(app)/config/CategoriesTab.tsx](../../../frontend/src/app/(app)/config/CategoriesTab.tsx)) chama o endpoint legacy `/config/categories` que **não conhece** o template global v1 ([ADR-137](../../adr/137-categorization-templates-overrides.md)). Workspace novo abre tela vazia. Endpoints modernos `/config/category-overrides/*` existem mas estão sem cliente.
>
> **Escopo V1:** editar as 24 categorias default (16 expense + 8 income) — label, keywords, monthly cap, disabled. **Fora:** custom categories, override de metadata auxiliar (`pj_source_mapping`, `internal_transfer_patterns`, etc.), audit log event-sourced, deprecation do endpoint legacy.
>
> **Lane independente em A11** (não ocupa W5, que está cheia). Precedente: `A11.competitive-pierre`.

---

## Resumo executivo

- Refatorar UX e contrato de leitura para que workspace novo veja as 24 categorias default + edite-as via UI; persistência em `workspace_category_overrides` (diff vs. template).
- Pré-requisito: bug latente de cache invalidation no fluxo de upsert/delete de override (stale até 300s no E4).
- Política v1→v2 do template **sem `template_version_pinned`**: migrations futuras codificam preserve/rename/disable explicitamente; mudança semântica sem rename é invariante proibida.
- 4 ondas, 4 PRs, 1 ADR Proposto. Wall-clock estimado: 6-7 dias com 3 agentes paralelos (W1+W2+W3) → W4.

## NEXT UP

| ID | Title | Effort | Severity | Owner agent | Why now |
|----|-------|--------|----------|-------------|---------|
| W1-T01 | Fix cache invalidation + `CategoryOverrideService` | M | P0 | senior-cto | Bug latente já em prod; bloqueia `read-after-write` da W4 |
| W2-T01 | Schema delta — `updated_by_user_id` + DTO version fields | S | P1 | data-engineer | Não-breaking; libera sinal v2 no DTO consumido pela W4 |
| W3-T01 | ADR-185 Proposto (política + escopo + invariantes) | S | P1 | product-manager + senior-cto | Gate CLAUDE.md §"ADR Proposto antes de PR P0/P1" |

## Index

| ID | Title | Wave | Status | Owner | Severity | Effort | Deps |
|----|-------|------|--------|-------|----------|--------|------|
| W1-T01 | Cache invalidation + `CategoryOverrideService` | W1 | ready | senior-cto | P0 | M | — |
| W2-T01 | Schema delta — `updated_by_user_id` + DTO version | W2 | ready | data-engineer | P1 | S | coordenar Alembic head |
| W3-T01 | ADR-185 Proposto | W3 | ready | product-manager | P1 | S | — |
| W4-T01 | UI refactor — CategoriesTab + useCategoriesAndMembers | W4 | blocked | product-designer | P1 | L | W1 ∪ W2 ∪ W3 mergeados |

## Quick Wins

- **W3-T01** (docs-only, fast-track per CLAUDE.md §"Exceção docs-only"): redação serial pequena, ~150 linhas, sem CI gate de runtime.
- **W2-T01**: migration trivial (1 coluna nullable, sem backfill); risk maior é coordenar `alembic heads` com lanes em voo.

## Premissas e não-objetivos

**Premissas:**

- Endpoints `/config/category-overrides/*` ([backend/app/api/category_overrides.py](../../../backend/app/api/category_overrides.py)) são estáveis e testados (entregues em A7.3).
- `category_template` v1 ([backend/alembic/versions/a5b6c7d8e9f0_seed_category_template_v1.py](../../../backend/alembic/versions/a5b6c7d8e9f0_seed_category_template_v1.py)) é fonte canônica das 24 keys.
- Cache TTL 300s em [backend/app/services/category_cache.py](../../../backend/app/services/category_cache.py) é o vetor confirmado de stale.
- `/config/categories` legacy permanece vivo até cutover em lane futura (não-objetivo desta V1).

**Não-objetivos (V1):**

- Criar categoria custom fora do template — futura tabela `workspace_custom_categories`, ADR Proposto separado.
- Override de `pj_source_mapping` / `clt_source_mapping` / `internal_transfer_patterns` — futura tabela `workspace_income_source_mapping`.
- Audit log event-sourced de mudanças — `updated_by_user_id` cobre necessidade mínima; padrão Decision A7.2a só quando consultor profissional pedir.
- Sunset do endpoint legacy `/config/categories` — separar para lane `A12.cat-legacy-sunset`.
- Migration v1→v2 do template — só fixture de teste pending; v2 entra quando o produto pedir.
- Sub-tab "Regras promovidas" (consumida por V2.A do [PLAN-cat-learning-loop](../CAT_LEARNING_LOOP/_README.md) §V2.A) — V1 deixa **hook estrutural** em tabs extensíveis no `CategoriesTab.tsx` (array configurável de `{id, label, content}`, 1 entrada em V1), mas **não implementa** lista de regras nem mutations. Detalhes em [W4 track §Coordenação cross-lane](../../sprint/A11/tracks/category-overrides-ui-refactor.md).

## Decisões pré-acordadas

| # | Decisão | Onde aterrissa |
|---|---------|----------------|
| 1 | Política v1→v2 **sem** `template_version_pinned`: migration de seed v2 codifica preserve/rename/disable; mudança semântica sem rename = proibida | ADR-185 §1 |
| 2 | Escopo 24 default-only; custom + metadata override fora | ADR-185 §2 + W4 acceptance |
| 3 | Cache invalidation no `CategoryOverrideService` (application layer), write-through pós-commit | ADR-185 §3 + W1 |
| 4 | `updated_by_user_id` no schema (FK nullable, sem backfill) | ADR-185 §4 + W2 |
| 5 | Teste migration v1→v2 pending com 3 fixtures (preserve/rename/remove) | ADR-185 §5 + W3 |
| 6 | UI consome `/config/category-overrides/resolved` (legacy permanece) | W4 |
| 7 | Diff de keywords reconstruído **client-side** (Set ops) — chips em 3 estados | W4 |
| 8 | Switch "Usar nesta família" substitui ícone `Trash2` (mismatch — backend não destrói) | W4 |
| 9 | Reset com toast undo 8s; modal só quando descarta keywords | W4 |
| 10 | Sinal v2 desatualizada (`AlertCircle`) sem CTA — só visual | W4 |

---

## Wave 1 — Cache invalidation + Service layer

### [W1-T01] Fix cache invalidation + `CategoryOverrideService`

- **id:** W1-T01
- **owner_agent:** senior-cto
- **deps:** —
- **severity:** P0
- **effort:** M
- **status:** ready
- **related_adr:** ADR-185 §3 (a publicar em W3)
- **risk:** invalidação write-through pode não cobrir todos os call-sites do resolver — E4 lê direto, ignora service. Mitigação: teste end-to-end (não unit).
- **rollback_plan:** reverter PR; cache fica stale como hoje até nova tentativa.
- **files_touched:**
  - `backend/app/application/categorization/category_override_service.py` (novo)
  - `backend/app/repositories/workspace_category_override_repository.py` (thin)
  - `backend/app/api/category_overrides.py` (consome service)
  - `backend/tests/integration/test_category_override_cache.py` (novo)
- **acceptance_criteria:**
  - [ ] `CategoryOverrideService` recebe `CategoryOverrideConfig` (value object frozen, ADR-097 D3) — não aceita `dict`/`Path`.
  - [ ] `upsert/delete/reset` invalidam `category_cache` write-through pós-commit; idempotente em retry.
  - [ ] Teste de regressão end-to-end: upsert → leitura via resolver no mesmo workspace vê valor novo em <100ms (sem TTL warm-up).
  - [ ] Repository thin (zero lógica de cache).
  - [ ] `pytest backend/tests -q` verde.
- **test_command:** `pytest backend/tests/integration/test_category_override_cache.py -q`

## Wave 2 — Schema delta (não-breaking)

### [W2-T01] Schema delta — `updated_by_user_id` + DTO version fields

- **id:** W2-T01
- **owner_agent:** data-engineer
- **deps:** —
- **severity:** P1
- **effort:** S
- **status:** ready
- **related_adr:** ADR-185 §4
- **risk:** conflito de Alembic head com lanes em voo (W2-T05 do PLATFORM_REVIEW). Mitigação: `git fetch origin && alembic heads` antes de criar revision.
- **rollback_plan:** `alembic downgrade -1`; coluna nullable, zero impacto produtivo.
- **files_touched:**
  - `backend/alembic/versions/<ts>_add_updated_by_to_category_overrides.py` (novo)
  - `backend/app/models/category_template.py` (campo SQLAlchemy)
  - `backend/app/schemas/dto/category.py` (DTO `template_version_used` + `latest_template_version`)
  - `backend/app/services/category_resolver.py` (popula DTO)
  - `docs/reference/DB_SCHEMA_REFERENCE.md` (regerado)
  - `frontend/openapi-snapshot.json` (regerado via `make update-openapi-snapshot`)
- **acceptance_criteria:**
  - [ ] Migration adiciona `workspace_category_overrides.updated_by_user_id` (FK `users.id`, nullable, `on_delete=SET NULL`).
  - [ ] `ResolvedCategoryDTO` ganha `template_version_used: int` + `latest_template_version: int` (apenas DTO, não domain).
  - [ ] `dev/build_db_schema_reference.py` atualizado.
  - [ ] OpenAPI snapshot regenerado e comitado (ADR-109).
  - [ ] Migration up/down idempotente.
- **test_command:** `pytest backend/tests/test_alembic.py backend/tests/test_openapi_snapshot.py -q`

## Wave 3 — ADR-185 Proposto

### [W3-T01] ADR-185 — política de edição e evolução de overrides

- **id:** W3-T01
- **owner_agent:** product-manager (rascunho) → senior-cto (revisão final)
- **deps:** —
- **severity:** P1
- **effort:** S
- **status:** ready
- **related_adr:** [[ADR-137]] (relacionada — esta ADR suplementa política não fechada em ADR-137)
- **risk:** ADR descreve invariante "rename obrigatório em mudança semântica" que fica difícil de enforçar mecânicamente; pode ser violado em release v2 futura.
- **rollback_plan:** N/A — docs-only.
- **files_touched:**
  - `docs/adr/185-category-overrides-policy.md` (novo)
  - `docs/DECISIONS.md` (anchor histórico via `dev/check_adr_anchors.py --suggest`)
  - `docs/adr/137-categorization-templates-overrides.md` (frontmatter `relates_to: [[ADR-185]]`)
- **acceptance_criteria:**
  - [ ] ADR-185 com `status: Proposto`, `phase: A11`.
  - [ ] Cobre 5 pontos: política v1→v2 sem pin · escopo 24 default-only · cache invalidation no service · `updated_by_user_id` schema · teste migration pending com 3 fixtures.
  - [ ] Wikilinks bidirecionais: ADR-185 ↔ ADR-137.
  - [ ] Anchor em `docs/DECISIONS.md` shim.
  - [ ] `pre-commit run --all-files` verde (frontmatter, filename↔id, links, anchors).
- **test_command:** `pre-commit run --all-files`

## Wave 4 — UI refactor

### [W4-T01] CategoriesTab + useCategoriesAndMembers — `/config/category-overrides/resolved`

- **id:** W4-T01
- **owner_agent:** product-designer
- **deps:** W1-T01 (cache fix) · W2-T01 (DTO version fields) · W3-T01 (ADR-185 mergeada)
- **severity:** P1
- **effort:** L
- **status:** blocked
- **related_adr:** ADR-185 (todos os §)
- **risk:** lixeira atual induz expectativa de delete; substituir por switch sem migração visual gradual pode confundir power-user.
- **rollback_plan:** PR isolado revertendo `frontend/src/app/(app)/config/CategoriesTab.tsx` e `frontend/src/lib/api/config.ts`; backend não regride.
- **files_touched:**
  - `frontend/src/app/(app)/config/CategoriesTab.tsx`
  - `frontend/src/app/(app)/transactions/_components/useCategoriesAndMembers.ts`
  - `frontend/src/lib/api/config.ts` (novo `listCategoriesResolved`, mutations p/ `/category-overrides/{key}`)
  - `frontend/src/components/categories/CategoryChipDiff.tsx` (novo)
  - Vitest + Playwright `@critical` cases novos
- **acceptance_criteria:**
  - [ ] Workspace novo (sem overrides) renderiza 24 categorias com labels e keywords default — não mais tela vazia.
  - [ ] Edição de label/cap/keyword/`disabled` persiste via `PUT /category-overrides/{template_key}` e reflete na UI em <1s.
  - [ ] Próxima execução E4 vê valor novo em <2s p95 (gate W1).
  - [ ] Chips em 3 estados (herdada · adicionada · removida-em-accordion) com Set diff client-side.
  - [ ] Switch "Usar nesta família" (default ON) substitui `Trash2`. Botão "Adicionar categoria" removido em V1.
  - [ ] Modal de confirmação **só** quando reset descarta keywords; toast undo 8s.
  - [ ] Badge "Personalizada" condicional + filtro header "Apenas personalizadas".
  - [ ] `AlertCircle` (`var(--semantic-warning)`) quando `template_version_used < latest_template_version`; tooltip explica sem CTA.
  - [ ] Evento estruturado `category_override.created` logado (ADR-110), com `template_key` + `field_changed` (sem PII).
  - [ ] Vitest + Playwright `@critical` verdes; `dev/check_css_var_references.py` verde.
- **test_command:** `cd frontend && npm test -- --run && npm run test:e2e -- --grep @critical`

---

## Dependências entre ondas

```
W1 (cache) ─┐
W2 (schema)─┼─→ W4 (UI)
W3 (ADR)  ─┘
```

W1, W2, W3 são **independentes em files** (zero overlap esperado: W1 toca `application/`, W2 toca migrations + DTO, W3 toca `docs/adr/`). W4 espera os 3 mergearem antes de virar `Ready for review`.

## Critério de aceite global

- [ ] 4 PRs mergeados em `main` com CI verde (CLAUDE.md §"Concluído").
- [ ] ADR-185 status `Proposto` → `Decidido (Sprint A11.cat-overrides)` no merge do W3.
- [ ] Workspace novo → tela `/config` mostra 24 categorias.
- [ ] Edição → próxima execução E4 reflete em <2s p95.
- [ ] `pytest backend/tests tests -q` + `cd frontend && npm test -- --run` + `npm run test:e2e -- --grep @critical` verdes.
- [ ] OpenAPI snapshot atualizado (W2).
- [ ] Plano arquivado: `git mv docs/plan/CATEGORY_OVERRIDES_UX/_README.md docs/archive/CATEGORY_OVERRIDES_UX_PLAN-YYYY-MM-DD.md` + entrada ≤8 linhas em `docs/archive/README.md`.
- [ ] Smoke humano (5 min): criar override de label numa cat default, executar pipeline E4, ver categoria com label novo no relatório.

## Riscos e mitigações

| # | Risco | Probabilidade | Impacto | Mitigação |
|---|-------|---------------|---------|-----------|
| R1 | Invalidação write-through não cobre todos os call-sites do resolver (E4 lê direto) | Média | Alto | W1 acceptance #2 exige teste **end-to-end**, não unit. Auditar todos `category_cache.get*` em PR review. |
| R2 | Conflito Alembic com W2-T05 do PLATFORM_REVIEW | Alta | Médio | `git fetch && alembic heads` antes de criar revision; usar `alembic merge` se necessário. |
| R3 | Política v1→v2 sem pin trava migrations futuras se mudança semântica não renomear key | Baixa | Alto | ADR-185 §1 declara invariante explícito + teste de migration pending; CI roda fixture quando v2 vier. |
| R4 | Sinal v2 desatualizada (`AlertCircle`) sem CTA confunde usuário | Baixa | Baixo | Tooltip explica em 1 frase; `product-designer` valida copy em PR. |
| R5 | Endpoint legacy `/config/categories` segue divergente do moderno | Média | Médio | Header `Deprecation: true` no legacy em W4 (1 linha) + lane futura `A12.cat-legacy-sunset`. |

## Métrica de sucesso

**North Star:** % de workspaces ativos com ≥1 override custom, 30 dias após GA da W4. Target: ≥40%.

**Input metrics (instrumentação obrigatória em W4):**

- Adoption — evento `category_override.created` (log estruturado JSON, ADR-110), com `workspace_id` (sem PII), `template_key`, `field_changed`.
- Task success — `saved / attempted` >95% no PUT.
- Latency p95 edit→pipeline reflect <2s (gate cache fix).
- Health — taxa de erro 5xx em `PUT /category-overrides/{key}` <1% sustained 1h (alarme `sre-devops`).

**Anti-metric:** otimizar para "número médio de overrides por workspace" induz spam; distribuição saudável tem moda 2-4.

## Sequenciamento sugerido

```
Dia 0  → 3 PRs em paralelo:
         ├── PR-W1 (senior-cto):    Cache invalidation + CategoryOverrideService
         ├── PR-W2 (data-engineer): Migration updated_by_user_id + DTO version fields
         └── PR-W3 (PM → senior-cto): ADR-185 Proposto (docs-only fast-track)

Dia 1-2 → W3 mergeada (docs-only, sem CI gate de runtime).
       → W1 e W2 entram em revisão; CI verde.

Dia 2-3 → W1 e W2 mergeadas. Smoke local: edit override → reflect <2s.

Dia 3   → PR-W4 (product-designer): UI refactor. Inicia COM W1+W2+W3 em main.

Dia 5-7 → W4 mergeado. ADR-185 flipa Proposto → Decidido.
       → Smoke humano. Plano arquivado.
```

**Lock-ordering crítico:** W3 (ADR Proposto) **deve** estar em `main` antes de W4 abrir PR (CLAUDE.md §"ADR Proposto antes de PR P0/P1").

## Definition of Done

```bash
# Feature concluída quando:
# 1. 4 PRs mergeados em main + CI verde + smoke humano OK
# 2. ADR-185 em status Decidido (A11.cat-overrides)
# 3. Plano arquivado:
git mv docs/plan/CATEGORY_OVERRIDES_UX/_README.md \
       docs/archive/CATEGORY_OVERRIDES_UX_PLAN-YYYY-MM-DD.md
# 4. Entrada em docs/archive/README.md com ≤8 linhas
# 5. Métrica NSM lida 30 dias pós-W4 e registrada na ata da sprint
```

## Histórico de revisão

| Data | Autor | Mudança |
|------|-------|---------|
| 2026-05-10 | dono + Claude (orquestrador) | Publicação inicial — 4 ondas, 4 tracks, ADR-185 reservada |
