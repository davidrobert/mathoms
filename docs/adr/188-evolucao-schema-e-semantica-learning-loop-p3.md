---
id: ADR-188
type: adr
title: "Evolução de schema e semântica do learning loop em P3 (soft-delete, partial unique, revert_count split)"
status: Decidido
phase: "A12.P3"
date: "2026-05-11"
relates_to:
  - "[[ADR-186]]"
  - "[[ADR-187]]"
supersedes: []
superseded_by: []
aliases: ["ADR 188", "Learning loop P3 schema", "Soft-delete categorization rules"]
size_lines: 229
tags:
  - area/categorization
  - area/db
  - area/backend
  - methodology/auvp
  - phase/a12
  - status/decidido
  - type/adr
---

> Supersedure parcial de [[ADR-186]] §D3 (schema) e §D6 (telemetria de
> revert). Decisões D1–D8 abaixo são acréscimos consistentes com a ADR
> canônica — não a invalidam, apenas refinam contratos pós-gate triple
> da P2 (PR #194). Wikilink bidirecional preservado em `relates_to`.

## §1 — Contexto

Pós-P2 (PR #194 — `CategorizationRulesV2` + adapter + sticky-manual +
mês fechado), o gate triple (financial-planner + data-engineer +
senior-cto) identificou **7 ressalvas** que materializam em P3 (Backend
API) como **evolução de schema e semântica de telemetria**:

1. Race em INSERT concorrente de `TransactionOverride(source='rule')` —
   adapter P2 mitigou com pre-load + skip, mas é otimização, não
   safety net.
2. Hard-delete de regra perde rastreabilidade do consultor profissional
   revisando histórico — viola caso de uso B2B2C.
3. `revert_count` único da [[ADR-186]] §D6 mistura **dois sinais
   distintos**: "regra ruim" (override `source='rule'` virou
   `source='manual'` com categoria diferente) vs. "abandono" (`DELETE
   /rules/{id}` sem evidência de qualidade da regra).
4. Idempotência de `POST /rules` precisa de garantia DB-side — header
   `Idempotency-Key` adiciona surface complexity para MVP single-tenant.
5. `_HARD_CAP=200` está hard-coded em P2 — endpoint P3 vai precisar do
   mesmo valor; constante compartilhada evita drift.
6. Cap exceeded retorna o quê? — sem semântica clara, frontend não
   diferencia "warning" (perto do limite) de "erro" (excedeu).
7. Conflito de keyword (mesma `keyword_normalized` + `target_category`
   diferentes) precisa contrato — bloquear criação seria UX ruim; aceitar
   sem disclosure é silencioso.

[[ADR-186]] §D3 (schema) e §D6 (telemetria) precisam **supersedure
parcial** para acomodar essas decisões.

## §2 — Decisões

### D1 — Soft-delete em `transaction_overrides`

`ADD COLUMN deleted_at TIMESTAMPTZ NULL` em `transaction_overrides`.
Hard-delete perde rastreabilidade do consultor profissional revisando
histórico de categorizações revertidas (caso de uso B2B2C).
**Read-path E4 consome view materializada
`transaction_overrides_active`** (filtro `WHERE deleted_at IS NULL`) —
encapsula complexidade num só lugar; serviços downstream continuam
agnósticos da coluna nova.

### D2 — Partial unique indexes (race protection DB-side)

Dois índices únicos parciais cobrem invariantes de concorrência:

- `UNIQUE (workspace_id, transaction_hash) WHERE source='rule' AND deleted_at IS NULL`
  — race protection sem precisar single-session lock; INSERT concorrente
  do mesmo override `source='rule'` em 2 workers cai em `ON CONFLICT DO
  UPDATE` atômico no DB.
- `UNIQUE (workspace_id, keyword_normalized, target_category) WHERE deleted_at IS NULL`
  — idempotência de `POST /rules` via DB constraint; usuário pode
  recriar regra após soft-delete (registro original tem `deleted_at NOT
  NULL`, fora do filtro).

Substituem necessidade de header `Idempotency-Key` para MVP — overhead
de invalidação de cache (Redis TTL) é assimétrico vs. constraint DB.

### D3 — `revert_count` split em 2 colunas

Substitui `revert_count` único da [[ADR-186]] §D6:

- `revert_count_manual_edit INTEGER NOT NULL DEFAULT 0` — incrementa
  quando `TransactionOverride(source='rule')` vira `source='manual'` com
  categoria diferente. **Este é o KPI D6 "regra ruim"** — sinal forte de
  que a regra categorizou errado e o usuário corrigiu.
- `revert_count_rule_disabled INTEGER NOT NULL DEFAULT 0` — incrementa
  em `DELETE /rules/{id}` (soft-delete). **Sinal mais fraco** ("abandono"
  — usuário desativou mas não necessariamente porque categorizou errado;
  pode ter mudado de ideia, simplificado o setup, etc.).

KPI `% reversão` da [[ADR-186]] §D6 passa a usar **só
`revert_count_manual_edit`** no numerador — disable não polui métrica
de qualidade.

### D4 — Race protection contract: `INSERT ... ON CONFLICT`

Em ambos P2 (pipeline adapter) e P3 (endpoint), criação de
`TransactionOverride(source='rule')` usa:

```sql
INSERT INTO transaction_overrides (...)
VALUES (...)
ON CONFLICT (workspace_id, transaction_hash) WHERE source='rule' AND deleted_at IS NULL
DO UPDATE SET new_category = EXCLUDED.new_category, ...
```

**Migrar P2 junto no PR1 deste ADR** (anti-bug-factory — se P2 mantém
pre-load+skip e P3 usa ON CONFLICT, contrato diverge entre stages).
Pre-load+skip continua como otimização (evita roundtrip em caso
comum), mas o INSERT final tem `ON CONFLICT` como safety net.

### D5 — `applied_count` semantics

"Transações distintas categorizadas pela regra **desde criação**" — não
"matches por run". Definido para evitar inflação por re-run idempotente
do E4 (cenário: rodar pipeline 5× no mesmo workspace bumparia counter
para 5N em vez de N). Coluna `applied_count` denormalizada bumped na
mesma transação SQL que cria o `TransactionOverride(source='rule')`,
usando `INSERT ... ON CONFLICT DO NOTHING RETURNING` ou subquery
condicional para garantir 1-to-1 com inserts efetivos (não com tentativas).

### D6 — `_HARD_CAP=200` shared constant

Extraído para `pipeline/domain/services/categorization_service.py`
(constante module-level) ou módulo dedicado
`pipeline/domain/services/categorization_limits.py`. Adapter (P2) +
endpoint (P3) leem do mesmo lugar — drift impossível.

**Override por workspace:** `workspaces.rule_cap_override INTEGER NULL`
permite consultor profissional B2B2C subir cap para clientes com
necessidades específicas. Valor efetivo:
`COALESCE(workspaces.rule_cap_override, HARD_CAP)`.

### D7 — Cap 50 soft warning + 200 hard

Threshold dual:

- **Soft cap 50:** response body inclui
  `meta.warnings: [{code: "rule_count_near_soft_cap", current: 52,
  soft_cap: 50, hard_cap: 200}]`. Não bloqueia criação. UX P4 pode
  exibir banner.
- **Hard cap 200** (ou `workspace.rule_cap_override`): retorna **422
  Unprocessable Entity** com
  `error.code: "hard_cap_exceeded"`, `error.details: {current: 200, hard_cap: 200}`.

422 (não 409) porque a request é semanticamente válida — só o estado do
recurso impede; padrão FastAPI/RFC 4918.

### D8 — Conflito de keyword (mesma `keyword_normalized + target_category` diferentes)

Aceitar criação. Response body inclui:

```json
{
  "rule_id": "<novo>",
  "conflicts": [
    {"rule_id": "<existente>", "target_category": "Alimentação · Delivery", "priority": 100}
  ],
  "effective_winner": "<id da regra que ganha sort estável>"
}
```

Sort estável da [[ADR-186]] §D4 + §D5 (`priority desc, len(keyword)
desc, created_at asc, id asc`) resolve qual regra ganha o match
deterministicamente. UX P4 mostra "winner" no banner persistente da
transação (já contrato da [[ADR-186]] §D4 reversibilidade).

## §3 — Não-objetivos / Backlog explícito

Foram avaliados e **deliberadamente deferidos** do escopo P3:

- **Idempotency-Key header (RFC draft):** overhead de cache TTL +
  invalidação para MVP single-tenant não justifica vs. constraint DB
  partial unique (§D2). Revisitar se multi-user dogfood pedir.
- **`month_view_log` table** para confirmation de apply retroativo:
  deferido **P4 frontend** — depende de tabela nova + view dedicada;
  P3 retorna `requires_user_confirmation: true` no preview sempre que
  há matches em meses abertos (frontend decide UX).
- **Aho-Corasick / `re.compile()` alternation única** para perf de
  `narrative.upper()` em runs grandes: PR3 paralelo a P4, atrás de
  feature flag `MATHOMS_RULE_MATCH_AHO_CORASICK` default off.
  Benchmark: pyahocorasick vs. regex alternation vs. status quo
  (substring) — vencedor entra como default em sprint posterior.
- **`report_snapshot.categorization_state_hash`** ao publicar
  (sugestão `financial-planner` no co-design 2026-05-11): backlog
  A11.report-publication V2 — preserva contrato de imutabilidade
  estendendo snapshot com hash da árvore de categorias ativa no
  momento da publicação.

## §4 — Invariantes preservadas (D2/D3 da [[ADR-186]])

Esta ADR **não toca** as 3 invariantes-chave do learning loop:

- **Sticky manual:** `TransactionOverride(source='manual')` continua
  intocável. Regra que casaria a transação é skipada (query verifica
  `source='manual' AND deleted_at IS NULL` antes de INSERT). Soft-delete
  de override manual nunca acontece via learning loop — só via
  ação explícita de usuário.
- **Mês fechado imutável:** `report_publications.published_at IS NOT
  NULL` continua bloqueando criação retroativa de override (ADR-187 ·
  A11.report-publication). Helper sync existente em
  `backend/app/services/report_publication_service.py` (ou path
  equivalente shipped em A11) consultado no preview e no apply.
- **Transferências internas bloqueadas:** `transactions.is_internal_transfer
  = true` continua excluindo a transação do match — regras de usuário
  **não sobrepõem** `transferencias_internas` precedence
  ([[ADR-134]]/[[ADR-137]]). Preview contabiliza em campo dedicado
  `matches_blocked_internal_transfers` para diagnóstico, mas apply
  não cria override.

## §5 — Riscos arquiteturais e mitigações

| Risco | Mitigação |
|---|---|
| Deadlock em UPDATE `CASE WHEN` (bump de `applied_count` para N regras em batch). | Ordem determinística `ORDER BY workspace_id ASC, rule_id ASC` antes do bump. PostgreSQL e SQLite respeitam ordem dentro de transação. |
| Drift de sort de prioridade P2 ↔ P3 (regra acordada em fase A executa diferente em B). | Helper `sort_rules_canonical(rules: Iterable[LearnedRule]) -> tuple[LearnedRule, ...]` único em `pipeline/domain/services/categorization_service.py`. Adapter P2 e endpoint P3 importam de lá. Boundary preservado (puro domínio, sem DB). |
| Partial unique + soft-delete: ao disable rule, overrides `source='rule'` daquela rule_id ficariam ativos sem regra correspondente. | Cascade soft-delete em `DELETE /rules/{id}`: `UPDATE transaction_overrides SET deleted_at = NOW() WHERE rule_id = $1 AND source = 'rule' AND deleted_at IS NULL`. Manual intocado. |
| View materializada `transaction_overrides_active` defasada (REFRESH manual). | Implementar como **view normal** (não materialized) ou **trigger-based refresh** se perf exigir. Decisão final no PR1 com data-engineer. |

## §6 — Histórico

- **2026-05-10** — Sessão co-design (`product-manager` +
  `financial-planner` + `product-designer`) define invariantes do
  learning loop e modelo híbrido C-light + D-forte. [[ADR-186]] Proposto.
- **2026-05-10** — P1 [[ADR-186]] §D3 schema base shipped em PR #188
  (commit `2a36388`).
- **2026-05-10** — P2 [[ADR-186]] §D5 pipeline E4 shipped em PR #194
  (commit `ab69414`). Gate triple identifica 7 ressalvas.
- **2026-05-11** — Sessão co-design (`product-manager` + `senior-cto` +
  `financial-planner`) consolida ressalvas em **ADR-188 Proposto**.
  Schema evolution + telemetry semantics + cap contract +
  conflict disclosure.
- **2026-05-11** — PR1 (#196) shippa schema delta (soft-delete, partial
  unique, view, ON CONFLICT) + P2 adapter migrado para `ON CONFLICT`.
- **2026-05-11** — PR2 (#197) shippa services + 5 endpoints + 4 telemetria
  + 24 testes integration + feature flag `learning_loop_enabled` (default
  off, gate dogfood).
- **2026-05-11** — PR3 shippa async Celery apply (>500 matches), perf
  hardening (norm_desc cache, scoped overrides query, partial index
  read-path), sort canônico shared (`sort_rules_canonical` em pipeline
  domain), Aho-Corasick opt-in via `MATHOMS_RULE_MATCH_AHO_CORASICK`,
  `PreconditionFailedError` handler 403. **Flip Proposto → Decidido
  (A12.P3)**.
