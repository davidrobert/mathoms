---
id: A12.decision-code-autogen
type: lane
title: "Decision.code server-generated (UX cleanup + race fix)"
sprint: A12
status: shipped
priority: P1
branch_slug: decision-code-autogen
adrs:
  - "[[ADR-214]]"
prompt: "[[decision-code-autogen]]"
depends_on: []
parallel_with:
  - "[[A12.sunset-disk-artifact]]"
  - "[[A12.cat-learning-loop]]"
  - "[[A12.alocacao-v2]]"
tags:
  - type/lane
  - sprint/a12
  - status/shipped
  - priority/p1
  - area/backend
  - area/frontend
  - breaking/api
---

# A12.decision-code-autogen — Decision.code server-generated

> **ADR canônica:** [[ADR-214]] (Proposto) — extensão de [[ADR-136]] sobre
> quem gera `Decision.code` (D01..D{1,3}). Co-design `product-designer`
> + `senior-cto` + `data-engineer` (sessão 2026-05-15).
> **Track operacional:** [decision-code-autogen](../tracks/decision-code-autogen.md).

## Origem

Sessão 2026-05-15 — owner perguntou se o input "Código da decisão" em
modal de aceite de sugestão (em `/acao`) é interno e deveria ser
auto-gerado. Investigação descobriu:

1. **Race condition real:** `computeNextDecisionCode` calcula `D{N+1}`
   no client; duas abas em paralelo geram colisão e o segundo `INSERT`
   estoura `UNIQUE (workspace_id, code)` no backend.
2. **Vazamento UX:** input com `autoFocus` rouba protagonismo do CTA
   primário do modal; product-designer recomendou remoção nos dois
   modais (`AcceptDialog` + `ModifyDialog` em `/acao`, `DecisionFormDialog`
   em `/plano`).
3. **Quebra de padrão:** Mathoms nunca expõe identificadores gerenciados
   pelo sistema em form de criação (workspace `slug` só editável em
   settings após criação; categoria `code` vem do catalog global).

ADR-136 não decidiu quem gera o code — frontend assumiu por default
tácito. Esta lane fecha essa ambiguidade.

## Escopo

PR único cross-cutting (backend + frontend + migration + tests). Ver
[track operacional](../tracks/decision-code-autogen.md) §"Inventário"
para lista exata de arquivos e §"Etapas" para sequência dentro do PR.

**Inclui:**

- Migration Alembic adicionando `CHECK (code ~ '^D\d+$')` em `decisions`
  (`NOT VALID` + `VALIDATE` separados).
- `DecisionRepositoryProtocol.next_code(workspace_id) -> str` com
  `pg_advisory_xact_lock` + `MAX + 1` na mesma transação.
- `create_decision` use case aceita `code: str | None = None` (server-gen
  quando `None`).
- DTOs perdem `decision_code`: `AcceptSuggestionCommand`,
  `ModifySuggestionCommand`, `DecisionCreateCommand`.
- `SuggestionResponse` ganha `accepted_decision_code: str | None`
  (additive).
- Frontend remove `code` input em `SuggestionDialogs.AcceptDialog` +
  `.ModifyDialog` + `DecisionFormDialog`; deleta `computeNextDecisionCode`;
  toast pós-aceite exibe `"Decisão D{N} criada"`.
- Snapshot OpenAPI regenerado + tipos `frontend/src/generated/`
  regenerados.
- Teste de concorrência em `test_multi_worker_concurrency.py`.

**Out-of-scope:**

- Generalizar para `workspace_counters` table (Opção B descartada por
  YAGNI; [[ADR-214]] §Alternativas).
- Override editorial (pular números, ex.: `D10` reservado) — YAGNI.
- Code para outros aggregates (Reports `R01`, Goals etc.) — fora desta
  lane.
- Endpoint `GET /decisions/next_code` para preview no header do form de
  criação — descartado por simplicidade; toast pós-criação faz o
  trabalho.

## Gates

- [[ADR-214]] flippada `Proposto` → `Decidido (A12)` no merge.
- Migration up/down/up testada local; audit pré-`VALIDATE` registrado no
  PR description (`SELECT workspace_id, code FROM decisions WHERE code !~ '^D\d+$'`
  retorna 0 rows).
- Suíte verde: `pytest backend/tests -q`, `pytest tests -q`,
  `cd frontend && npm test -- --run`, `pre-commit run --all-files`.
- Teste novo `test_concurrent_decision_creation_no_code_collision` em
  [`backend/tests/integration/test_multi_worker_concurrency.py`](../../../../backend/tests/integration/test_multi_worker_concurrency.py)
  passa: 10 corrotinas paralelas → 10 codes únicos sequenciais, zero
  `IntegrityError`.
- Snapshot OpenAPI atualizado (`make update-openapi-snapshot`); diff
  esperado: remoção de `decision_code` em 2 commands + adição de
  `accepted_decision_code` em `SuggestionResponse`.
- Frontend build verde após regen de tipos.

## Riscos

| Risco | P | Mitigação |
|---|---|---|
| `CHECK` constraint quebra row legada (`code='M01'`, etc.) | P0 | Audit pré-merge listado no PR description; se aparecer, decisão case-a-case antes de `VALIDATE` |
| Cliente externo dependendo de `decision_code` no body | P1 | Não há cliente externo formal; único consumer é frontend Next.js no mesmo PR ([[ADR-109]] governa auth, não estabilidade DTO) |
| Lock advisory contende em batch (agente IA aceita 5+ sugestões) | P2 | Carga típica serializa em ~5-25ms; telemetria `mathoms.decisions.next_code_lock_wait_ms` no use case revela contenção real |
| Use case interno (importer/migrator) quebra | P2 | `create_decision` mantém `code: str \| None = None` opcional; importer continua passando explícito |
| Form de criação manual em `/plano` perde contexto sem code visível | P2 | Header vira `"Nova decisão"` sem code; code aparece no card após criação. Toast educa: `"Decisão D03 criada"` |

## Definition of Done

- ☑ PR mergeado em `main` (squash) com CI verde — [#279](https://github.com/davidrobert/mathoms/pull/279), commit `2f1dae76`, 2026-05-15.
- ☑ [[ADR-214]] flippada `Proposto` → `Decidido (A12.decision-code-autogen)`.
- ☑ [[ADR-136]] mantém nota cross-link para [[ADR-214]] (já adicionada
  nesta lane).
- ☑ `grep -rn "decision_code" backend/app/schemas/dto/` — hits remanescentes
  são apenas docstrings documentando a remoção (campo real deletado).
- ☑ `grep -rn "computeNextDecisionCode" frontend/src/` — hit remanescente é
  comentário em `InboxTab.tsx` documentando a deleção (função real deletada).
- ☑ Snapshot OpenAPI atualizado e comitado (PR #279).
- ☑ Test `test_concurrent_decision_creation_no_code_collision` vive em
  `backend/tests/integration/test_multi_worker_concurrency.py`, estável no CI.
- ☑ CHANGELOG entry —
  [CHG-2026-05-15-REFACTOR-DECISION-CODE-AUTOGEN](../changelog/CHG-2026-05-15-REFACTOR-DECISION-CODE-AUTOGEN.md)
  (pós-DOC_REORG, entries vivem em `docs/sprint/<X>/changelog/`).

## Status (reconciliação 2026-07-08)

Lane **entregue em `main`** em 2026-05-15 (PR #279, squash `2f1dae76`);
[[ADR-214]] `Decidido`. Frontmatter estava stale (`in_progress`) desde a
pausa da sprint ([[ADR-234]]); reconciliado nesta data com verificação
código-contra-DoD (greps + test + snapshot).

## Estimativa

~1-1.5d eng (1 PR cross-cutting; sem soak/canary — mudança contida).

## Links

- ADR canônica: [[ADR-214]]
- Track: [decision-code-autogen](../tracks/decision-code-autogen.md)
- Estende: [[ADR-136]] (Decision aggregate)
- Aderente a: [[ADR-111]] (stateless), [[ADR-097]] D3 (ISP), [[ADR-109]] (OpenAPI snapshot)
