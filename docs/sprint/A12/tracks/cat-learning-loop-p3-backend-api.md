---
id: TRACK-cat-learning-loop-p3-backend-api
type: track
title: "Track Cat Learning Loop P3 — Backend API + schema evolution"
lane: "[[A12.cat-learning-loop]]"
sprint: A12
plan: PLAN-cat-learning-loop
status: ready
created_at: "2026-05-11"
consumed_at: null
agent_role: "senior-cto + data-engineer"
tags:
  - type/track
  - sprint/a12
  - status/ready
  - area/categorization
  - area/backend
  - area/db
---

# Track Cat Learning Loop P3 — Backend API + schema evolution

> **Lane:** [[A12.cat-learning-loop]] · **Plano canônico:**
> [PLAN-cat-learning-loop](../../../archive/CAT_LEARNING_LOOP-2026-07-08.md) §P3
> · **ADRs canônicas:** [[ADR-186]] (base, Decidida) + [[ADR-188]]
> (schema evolution + telemetry semantics, Proposto — flippa para
> Decidida no merge do PR estrutural).
> · **Branch prefix:** `agent/cat-learning-loop-p3-<sub>/<yyyyMMdd-HHmm>`
> (um por PR — `schema`, `services`, `async`).
> · **Depende de:** P1 ✅ (PR #188), P2 ✅ (PR #194), [[ADR-188]] Proposto
> mergeada antes do PR1 do track.
> · **Bloqueia:** P4 (frontend) condicional a **gate dogfood** entre PR2 e PR3.

## Briefing

P1 entregou schema base; P2 entregou pipeline E4 com `CategorizationRulesV2`
+ invariantes. P3 entrega **endpoints HTTP** + **schema evolution** que
suporta o ciclo completo CRUD da regra com telemetria de saúde e
preview retroativo seguro (mês fechado + manual sticky enforced).

Quebrado em **3 PRs sequenciais** para isolar risco e habilitar dogfood
intermediário:

1. **PR1 — Schema delta + P2 migration `ON CONFLICT` + `_HARD_CAP` shared** (~1.5d)
2. **PR2 — Application services + endpoints + telemetria** (~2.5d)
3. **PR3 — Async Celery apply + perf hardening** (~1.5d, paralelo a P4)

Total: ~5.5d engineering + gate dogfood 7d wall-clock entre PR2 e PR3/P4.

## PR1 — Schema delta + P2 migration `ON CONFLICT` + `_HARD_CAP` shared (~1.5d)

### Migration Alembic

- `transaction_overrides ADD COLUMN deleted_at TIMESTAMPTZ NULL` (soft-delete).
- `categorization_rules`:
  - `ADD COLUMN revert_count_manual_edit INTEGER NOT NULL DEFAULT 0`
    (substitui semântica do `revert_count` original — verificar uso em
    main; se já consumido, renomear via `ALTER COLUMN`; se zero usage,
    drop + recreate).
  - `ADD COLUMN revert_count_rule_disabled INTEGER NOT NULL DEFAULT 0`.
- `workspaces ADD COLUMN rule_cap_override INTEGER NULL`.
- Partial unique indexes (PostgreSQL syntax — SQLite tem suporte
  parcial, validar com data-engineer):
  - `CREATE UNIQUE INDEX uq_txov_active_rule ON transaction_overrides
    (workspace_id, transaction_hash) WHERE source='rule' AND deleted_at IS NULL`.
  - `CREATE UNIQUE INDEX uq_categorization_rule_workspace_keyword_target_active
    ON categorization_rules (workspace_id, keyword_normalized, target_category)
    WHERE deleted_at IS NULL`.
- View (não materializada por simplicidade — promover se perf exigir):
  `CREATE VIEW transaction_overrides_active AS SELECT * FROM
  transaction_overrides WHERE deleted_at IS NULL`.

### `_HARD_CAP=200` shared constant

Extrair de adapter P2 para `pipeline/domain/services/categorization_service.py`
(módulo já existente — não criar `categorization_limits.py` para
manter footprint mínimo; revisitar se módulo crescer). Adapter P2 +
endpoint P3 importam:

```python
from pipeline.domain.services.categorization_service import RULE_HARD_CAP, RULE_SOFT_CAP
```

### Refactor `backend/app/services/categorization_learning_loop.py` (P2)

Substituir manual INSERT por `INSERT ... ON CONFLICT DO UPDATE`
(ADR-188 §D4). Pre-load + skip mantém-se como otimização (evita
roundtrip em caso comum), mas DB constraint é safety net contra race
em workers concorrentes.

### Critério de aceite PR1

- [ ] Alembic up/down idempotente (testar com `alembic upgrade head &&
      alembic downgrade -1 && alembic upgrade head`).
- [ ] `dev/check_pipeline_boundaries.py` verde — constante em
      `pipeline/domain/services/` não importa SQLAlchemy.
- [ ] Goldens E4 inalterados para workspace sem regras (`pytest tests -q`).
- [ ] Property-based test concurrent insert (`hypothesis` ou
      `concurrent.futures.ThreadPoolExecutor`) — 100 inserts paralelos
      do mesmo `(workspace_id, transaction_hash, source='rule')`
      resultam em 1 row + N-1 `ON CONFLICT DO UPDATE`.
- [ ] `pytest backend/tests tests -q` verde.
- [ ] `pre-commit run --all-files` verde.

## PR2 — Application services + endpoints + telemetria (~2.5d)

### Application services

- `backend/app/application/categorization/rule_preview_service.py` —
  computa matches em meses abertos/fechados + conflitos + warnings.
  **Sem persistência** (preview puro).
- `backend/app/application/categorization/rule_management_service.py` —
  create + apply (síncrono até 500 overrides) + delete (soft) +
  disable (toggle sem cascade) + list (paginado).
- `backend/app/application/categorization/mappers.py` —
  `LearnedRule` (domain) ↔ `CategorizationRuleDTO` (HTTP). Garante
  isolamento de schema interno vs. wire.

### Endpoints (5)

Todos com `response_model` explícito ([[ADR-102]] R18 · [[ADR-109]]):

**1. `POST /workspaces/{ws}/categorization/rules/preview`**

Request body:
```json
{"keyword": "MERCADO PAGO IFOOD", "target_category": "Alimentação · Delivery", "period_window": null}
```

Response (`PreviewResponse`):
```json
{
  "matches_total": 47,
  "matches_in_closed_months": 12,
  "matches_with_manual_override": 3,
  "matches_blocked_internal_transfers": 1,
  "matches_amount_total_brl_cents": 234500,
  "matches_by_month": [{"month": "2026-01", "count": 8, "is_closed": false}, ...],
  "conflicts": [{"rule_id": "<uuid>", "target_category": "Lazer", "priority": 100}],
  "low_risk": false,
  "requires_user_confirmation": true,
  "warnings": [{"code": "keyword_too_short", "details": {...}}]
}
```

Validações:
- `keyword` <4 chars → warning `keyword_too_short` (não bloqueia).
- Match em `transactions.is_internal_transfer = true` → contabiliza em
  `matches_blocked_internal_transfers`, **NÃO** entra no apply
  (invariante ADR-188 §4).
- `requires_user_confirmation: true` sempre que
  `matches_in_closed_months > 0` (P3 entrega o sinal; P4 entrega a UX).

**2. `POST /workspaces/{ws}/categorization/rules`** (commit)

Request body igual ao preview. Aplica retroativo em meses abertos
(skip mês fechado + skip manual sticky enforced em SQL). Até 500
overrides → síncrono. Acima → `202 Accepted` + `Location` para
`/rules/{id}/apply-status` (delivery em PR3).

Response 200 (`CreateRuleResponse`):
- `rule_id`, `applied_count` (overrides criados nesta operação),
  `conflicts` (lista, vazia se nenhum), `effective_winner` (ADR-188 §D8).

Response 422 (`hard_cap_exceeded`): body `{error: {code, details}}`.
Response 409 (`exact_duplicate`): mesma `(workspace, keyword, target)`
ativa já existe (partial unique constraint).

**3. `DELETE /workspaces/{ws}/categorization/rules/{id}`**

Soft-delete cascade: `UPDATE categorization_rules SET deleted_at =
NOW() WHERE id = $1; UPDATE transaction_overrides SET deleted_at =
NOW() WHERE rule_id = $1 AND source = 'rule' AND deleted_at IS NULL`.
Manual intocado. Bump `revert_count_rule_disabled` no rule_id antes do
soft-delete (mesmo flush). Response 204.

**4. `GET /workspaces/{ws}/categorization/rules`** (list paginado)

Query params: `enabled` (filter), `page`, `page_size`. Response
(`ListRulesResponse`): `items: [CategorizationRuleDTO]`, `total`,
`page`, `page_size`. DTO expõe `applied_count`,
`revert_count_manual_edit`, `revert_count_rule_disabled` separados.

**5. `POST /workspaces/{ws}/categorization/rules/{id}/disable`**

Toggle `enabled` boolean **sem cascade** — preserva overrides
`source='rule'` históricos (mês fechado fica imutável). Re-enable não
re-aplica retroativo (decisão de UX P4). Idempotente. Response 200 com
DTO atualizado.

### Telemetria — 4 contadores `mathoms.categorization.*`

Instrumentado via `backend/app/core/logging.py` (`MathomsJsonFormatter`)
ou OTel meter direto (`backend/app/core/otel.py`):

- `mathoms.categorization.transactions_categorized_total{source}` —
  counter por source (`manual|rule|template|uncategorized`).
  Incrementado no flush de qualquer override criação OU no E4 ao
  resolver categoria.
- `mathoms.categorization.rules_applied_total{workspace_id}` — counter
  no flush de `INSERT INTO categorization_rules`.
- `mathoms.categorization.rules_reverted_total{workspace_id, mode}` —
  counter; `mode` ∈ `{transaction_edit, rule_delete}`.
  - `transaction_edit` quando `TransactionOverride(source='rule')` vira
    `source='manual'` (bump `revert_count_manual_edit` na mesma SQL
    transaction).
  - `rule_delete` no `DELETE /rules/{id}` (bump
    `revert_count_rule_disabled`).
- `mathoms.categorization.time_to_rule_seconds{workspace_id}` —
  histogram; computado em `POST /rules` como
  `now() - first_override.created_at` (override mais antigo de
  `target_category` no workspace, se houver).

### Feature flag

`workspaces.learning_loop_enabled BOOLEAN NOT NULL DEFAULT false`.
Endpoints retornam **404** se `learning_loop_enabled = false`
(não 403 — recurso "não existe" para esse workspace; padrão FastAPI).
Workspace do CEO dogfood: flag manualmente `true` via migration data
seed ou endpoint admin.

### Critério de aceite PR2

- [ ] 5 endpoints com `response_model` explícito; OpenAPI snapshot
      atualizado (`make update-openapi-snapshot`).
- [ ] Tests integration: 5-7 cases por endpoint (especificação em
      §Testes integration abaixo). 24 testes total mínimo.
- [ ] `dev/check_pipeline_boundaries.py` verde — application services
      não vazam SQLAlchemy para domain.
- [ ] 4 contadores instrumentados; verificar via OTEL local stack ou
      logs estruturados em teste de integração.
- [ ] Feature flag enforce — workspace sem flag retorna 404 em todos
      os endpoints.
- [ ] `pytest backend/tests tests -q` verde.
- [ ] `pre-commit run --all-files` verde.

## PR3 — Async Celery apply + perf hardening (~1.5d, paralelo a P4)

### Async apply

Celery task `apply_rule_retroactive_task(rule_id: str, workspace_id: str)`
em `backend/app/tasks/categorization.py`. Idempotente (re-run não
re-aplica via partial unique constraint da PR1). Trigger em `POST
/rules` quando matches > 500 (síncrono < 500 evita complexidade UX para
caso comum).

Endpoint novo: `GET /workspaces/{ws}/categorization/rules/{id}/apply-status`
retorna `{state: PENDING|STARTED|SUCCESS|FAILURE, progress: 0-100,
overrides_created: int}`. Polling do frontend P4.

### Perf hardening

- **UPDATE CASE WHEN** para bump batch de `applied_count` (N regras
  numa run = 1 UPDATE em vez de N). Ordem determinística
  `ORDER BY workspace_id, rule_id` previne deadlock.
- **Aho-Corasick** (lib `pyahocorasick`) ou **`re.compile()`
  alternation única por load** vs. status quo (substring scan por
  regra). Atrás de feature flag
  `MATHOMS_RULE_MATCH_AHO_CORASICK` default off. Benchmark obrigatório
  pré-flip (suite com 200 regras + 10k transações).

### Critério de aceite PR3

- [ ] Celery task idempotente (re-run não duplica overrides — partial
      unique cobre).
- [ ] `GET .../apply-status` endpoint com `response_model`.
- [ ] UPDATE CASE WHEN batch testado (1 UPDATE para N rules).
- [ ] Aho-Corasick atrás de feature flag default off + benchmark
      documentado em `docs/reference/RUNBOOK.md` §5.x.
- [ ] `pytest backend/tests tests -q` verde.
- [ ] `pre-commit run --all-files` verde.

## Gate de saída P3 → dogfood

Critérios para mergear PR2 e habilitar gate dogfood:

- Suite verde: `pytest backend/tests tests -q` + `pre-commit run
  --all-files`.
- OpenAPI snapshot atualizado.
- [[ADR-188]] flippada para `Decidido (Sprint A12.P3)` no merge do PR2
  (ou PR3 se houver mudança de contrato — decisão final no PR).
- Feature flag `learning_loop_enabled` default `false`.
- Workspace do CEO com flag manual `true` + Celery `--concurrency=1`
  (até PR3 mergear — evita race no `applied_count` UPDATE).
- Documentação dogfood CLI/curl em `docs/reference/RUNBOOK.md` §5.x
  (curl + jq examples para preview/create/disable/delete).

## Gate dogfood (entre PR2 e PR3, 7d wall-clock)

**Owner:** CEO + `product-manager`. **Objeto observado:** workspace do
CEO com flag `learning_loop_enabled = true`. **Critérios:**

- ≥5 regras persistentes (não revertidas no mesmo dia).
- `revert_rate ≤ 30%` agregado — numerador:
  `revert_count_manual_edit` somado das regras; denominador:
  `applied_count` somado. (Disable não conta — semântica ADR-188 §D3.)
- ≥3 regras geraram ≥3 matches retroativos cada (efeito real, não
  só intent).
- **Entrevista qualitativa 3 perguntas** (CEO responde em texto livre,
  PM consolida):
  - (a) Quando a regra rodou retroativamente, ela apareceu na 1ª
    categoria certa para você?
  - (b) Houve momento em que você reverteria a regra? Por quê?
  - (c) Se começasse do zero, criaria essa regra de novo?

**Resultado:**

- **Falha** (qualquer critério não bate) → `product-designer` reabre
  extração de keyword + UX (P4 vai para Roadmap, não Now). PR3
  continua se houver bugs do PR2 a corrigir.
- **Sucesso** → PR3 mergea + P4 (frontend) abre em paralelo (track
  separado `cat-learning-loop-p4-frontend-edit.md`).

## Testes integration (5-7 cases por endpoint)

### `POST /rules/preview` (5)

1. Shape obrigatório: response tem todos os campos do `PreviewResponse`
   schema, com tipos corretos.
2. Mês fechado conta em `matches_in_closed_months` mas
   `requires_user_confirmation = true`; não aplica no commit
   subsequente.
3. Manual override conta em `matches_with_manual_override` mas
   não entra no apply (skip silencioso no commit).
4. Conflito de keyword listado em `conflicts` com `rule_id` +
   `target_category` + `priority`.
5. `period_window: {start, end}` filtra `matches_by_month` ao
   intervalo (zero matches fora retorna lista vazia, não erro).

### `POST /rules` (7)

1. Apply retroativo cria N overrides em meses abertos sem manual; DB
   row count bate com `applied_count` retornado.
2. Mês fechado rejeitado por txn (skip silencioso); request não falha,
   só `applied_count` é menor que `matches_total` do preview.
3. Manual preservado (override `source='manual'` da `transaction_hash`
   X continua com mesma `new_category` pós-apply).
4. Conflito exato `(workspace, keyword, target)` ativo → **409
   Conflict** com `error.code: "exact_duplicate"`.
5. Conflito keyword + target diferente → **200 OK** + `conflicts: [...]`
   no body + `effective_winner` populated.
6. Cap soft 50 atingido → **200 OK** + `meta.warnings:
   [{code: "rule_count_near_soft_cap"}]`.
7. Cap hard 200 atingido → **422 Unprocessable Entity** +
   `error.code: "hard_cap_exceeded"`.

### `DELETE /rules/{id}` (5)

1. Soft-delete: `categorization_rules.deleted_at IS NOT NULL` pós-call.
2. Cascade: `transaction_overrides.deleted_at IS NOT NULL` para todos
   os `(rule_id, source='rule', deleted_at IS NULL)`. Manual intocado.
3. Telemetria: `rules_reverted_total{mode=rule_delete}` increment + bump
   de `revert_count_rule_disabled` em `categorization_rules`.
4. Recriar pós-delete: `POST /rules` com mesma `(keyword, target)` não
   conflita (partial unique exclui `deleted_at IS NOT NULL`).
5. Idempotente: 2× `DELETE` mesmo `id` → 1ª retorna 204, 2ª retorna 404
   (rule já com `deleted_at`).

### `GET /rules` (4)

1. Paginação: `page=1, page_size=10` retorna `items.length <= 10` +
   `total` correto.
2. `applied_count` histórico preservado (regra criada em jan, deletada
   em mar — GET pós-delete não lista; com `?include_deleted=true`
   retorna com `applied_count` original).
3. `revert_count_manual_edit` e `revert_count_rule_disabled` retornados
   separadamente no DTO.
4. Filtro `enabled=true` exclui regras com `enabled=false` (disable
   sem cascade) mas inclui regras com matches históricos.

### `POST /rules/{id}/disable` (3)

1. Toggle: `enabled: true → false` sem cascade (overrides
   `source='rule'` históricos preservados).
2. Re-enable: `enabled: false → true` não re-aplica retroativo (apply
   só via `POST /rules` original ou re-criação).
3. Idempotente: 2× chamadas no mesmo state retornam 200 sem mudança.

## Riscos

| Risco | Mitigação |
|---|---|
| Drift de comportamento P2 (`pre-load + skip`) ↔ P3 (`ON CONFLICT`). | PR1 migra P2 para `ON CONFLICT` mesmo PR — anti-bug-factory. |
| Property test de concorrência flaky (SQLite). | Skip em SQLite com `pytest.mark.skipif(SQLITE)`; rodar em CI PostgreSQL. |
| Celery task com `applied_count` race em workers paralelos. | Dogfood com `--concurrency=1` até PR3 entregar UPDATE CASE WHEN ordenado. |
| Aho-Corasick adiciona dep nativa (`pyahocorasick` tem C extension). | Feature flag default off; build wheel pre-compiled em `requirements/`. |
| View `transaction_overrides_active` defasada em PostgreSQL com replica lag. | View regular (não materializada) — sempre fresh. Promover para matview só se medição mostrar gargalo. |

## Arquivos esperados

### PR1
- **Novo:** `alembic/versions/XXXX_p3_soft_delete_and_partial_unique.py`
- **Editado:** `pipeline/domain/services/categorization_service.py`
  (constantes `RULE_HARD_CAP`, `RULE_SOFT_CAP`).
- **Editado:** `backend/app/services/categorization_learning_loop.py`
  (P2 — `INSERT ... ON CONFLICT DO UPDATE`).
- **Editado:** `backend/app/models/transaction_override.py` +
  `categorization_rule.py` (campos novos).
- **Novo:** `backend/tests/test_categorization_rules_concurrent_insert.py`
  (property-based).

### PR2
- **Novo:** `backend/app/application/categorization/rule_preview_service.py`
- **Novo:** `backend/app/application/categorization/rule_management_service.py`
- **Novo:** `backend/app/application/categorization/mappers.py`
- **Novo:** `backend/app/api/categorization_rules.py` (5 endpoints).
- **Novo:** `backend/app/schemas/categorization_rules.py` (Pydantic DTOs).
- **Editado:** `backend/app/main.py` (mount router).
- **Editado:** `backend/app/models/workspace.py`
  (`rule_cap_override`, `learning_loop_enabled`).
- **Novo:** `backend/tests/test_categorization_rules_api_*.py` (24+ tests).
- **Editado:** `backend/tests/openapi_snapshot.json` (regen).

### PR3
- **Novo:** `backend/app/tasks/categorization.py`
- **Editado:** `backend/app/api/categorization_rules.py`
  (`GET .../apply-status`).
- **Editado:** `backend/app/services/categorization_learning_loop.py`
  (UPDATE CASE WHEN batch + Aho-Corasick atrás de feature flag).
- **Novo:** `backend/tests/test_categorization_rules_async_apply.py`
- **Editado:** `docs/reference/RUNBOOK.md` §5.x (dogfood CLI/curl).

## Testes (comandos)

```bash
pytest backend/tests/test_categorization_rules_concurrent_insert.py -q   # PR1
pytest backend/tests/test_categorization_rules_api_*.py -q               # PR2
pytest backend/tests/test_categorization_rules_async_apply.py -q         # PR3
pytest backend/tests -q
pytest tests -q
pre-commit run --all-files
make update-openapi-snapshot                                              # PR2
```

## Ligações

- Plano: [PLAN-cat-learning-loop](../../../archive/CAT_LEARNING_LOOP-2026-07-08.md) §P3
- ADR base: [[ADR-186]] (Decidida, §D3 schema + §D6 telemetry parcialmente
  superseded por [[ADR-188]]).
- ADR P3: [[ADR-188]] (Proposto, schema evolution + telemetry semantics +
  cap contract + conflict disclosure).
- Pré-req schema: PR #188 (P1), commit `2a36388`.
- Pré-req pipeline: PR #194 (P2), commit `ab69414`.
- Pré-req mês fechado: PR #185 ([[ADR-187]]), commit `182308a`.
- Lane: [[A12.cat-learning-loop]].
- Track P2 (Decidido): `cat-learning-loop-p2-pipeline.md`.
- Track P4 (próximo, condicional ao gate dogfood):
  `cat-learning-loop-p4-frontend-edit.md` (criado quando gate passar).
