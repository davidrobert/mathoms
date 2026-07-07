---
id: A30.l1
type: lane
title: "editor de budget LLM por workspace no console interno (ops)"
sprint: A30
plan: PLAN-internal-admin
status: shipped
ship_pr: 815
ship_date: "2026-07-07"
priority: P1
branch_slug: ops-llm-budget-editor
adrs: ["[[ADR-116]]", "[[ADR-173]]"]
depends_on: []
tags:
  - type/lane
  - sprint/a30
  - status/shipped
  - priority/p1
  - area/internal-ops
---

# A30.l1 — `ops-llm-budget-editor` (backend service + PATCH + UI ops · sem ADR nova)

## Problema

`workspaces.monthly_llm_budget_usd` ([[ADR-173]]: warn 80%, hard-stop 110%,
janela mês-calendário UTC, `NULL` = sem cap) só é editável via SQL direto no
DB. Caso real (2026-07-06): dogfood do owner abortou em `extract_irpf_full`
com cap $5 / gasto $5.57; unblock foi `UPDATE` manual em produção-dev —
exatamente a classe de operação que o console interno ([[ADR-116]], IA-0
entregue) existe para eliminar. Multi-tenant torna o ajuste de cap operação
de rotina (upgrade de plano, cliente pesado, incidente de custo).

**Fora de escopo (Won't documentado):** expor budget ao usuário final
(self-service) — reabrir só quando houver pricing/tier (gatilho:
`gtm-strategist`).

## Escopo

### 1. Service (`backend/app/services/internal_ops/update_workspace_llm_budget.py`)

Molde: [update_workspace_business_profile.py](../../../../backend/app/services/internal_ops/update_workspace_business_profile.py)
(`_load_workspace` → mutação → `append_audit`; retorna `OpResult`).

- Payload tipado (Pydantic no boundary): `cap_usd: Decimal | None` +
  `remove_cap: bool = False`. **`NULL` só entra via `remove_cap=True`
  explícito** — nunca inferido de campo vazio/ausente (guardrail
  anti-uncap-acidental do sre-devops).
- Validação: `cap_usd ≥ 0`, `quantize(Decimal("0.01"))`, rejeita NaN e
  `cap_usd > MAX_SETTABLE_BUDGET_USD` (constante no service; inicial
  **US$ 1.000/mês** — clamp anti-typo de ordem de grandeza; calibrar com
  unit economics depois). Erro cita valor ofensor + shape esperado.
- Audit **hard-fail**: `AuditRecord(action="workspace.update_llm_budget",
  actor=…, target_type="workspace", target_id=ws_id,
  details={"previous": …, "current": …, "remove_cap": …})` com valores
  literais (budget não é PII; `_FORBIDDEN_KEYS` não o redige). Falha do
  sink = falha da operação, não best-effort.
- Log estruturado espelho `mathoms.internal_ops.budget_change` (ADR-110,
  `get_logger`) com actor/previous/current — correlacionável com os warns
  `llm.budget_warn` existentes. Se `current > 3 × previous`, WARNING de
  salto suspeito.
- **NÃO invalidar o cache Redis de gasto.** O cache guarda o SUM de gasto
  (TTL 60s); o cap é relido do DB a cada `check_budget()`
  ([llm_budget_service.py](../../../../backend/app/services/llm_budget_service.py)
  `_load_budget`) — efeito imediato por design; cap e gasto são ortogonais.

### 2. Endpoints (`backend/app/api/admin/workspaces.py` + `metrics.py`)

- `PATCH /admin/workspaces/{workspace_id}/llm-budget` — sob
  `require_internal_operator`, `response_model` explícito (ADR-102 R18);
  mapeia `OpResult.failure("workspace_not_found")` → 404.
- Leitura para a UI decidir informada: expor gasto do **mês-calendário UTC
  corrente** (paridade com `_current_month_window` do hard-stop). Atenção:
  `llm_cost_by_workspace` em
  [metrics.py](../../../../backend/app/api/admin/metrics.py) usa janela
  **rolling** `period_days` — mostrar rolling ao lado de cap mensal induz
  decisão errada na virada do mês (achado do product-manager). Solução
  mínima: novo `GET /admin/metrics/llm-budget` (ou campo novo no endpoint
  existente) com, por workspace: `spent_month_usd`, `cap_usd`,
  `pct_of_cap`, `status` (`ok | warn | hard_stop | uncapped`),
  `call_count`, `unknown_cost_calls`.
- Endpoints `/admin/*` fazem parte do snapshot OpenAPI: rodar
  `make update-openapi-snapshot` e commitar o diff (ADR-109).

### 3. UI (`frontend-ops/src/app/(admin)/metrics/page.tsx` ou página nova)

Seção "Custo LLM por workspace" (a tabela ainda não existe no ops — o
endpoint de leitura existe só no backend): workspace, gasto do mês, cap,
`pct_of_cap`, status em pill, `unknown_cost_calls`, ação **Editar cap**.

- Modal de edição mostra, **antes** de confirmar: gasto do mês corrente,
  cap atual e **status resultante do novo cap** (OK / warn ≥80% /
  hard-stop ≥110%) — o operador vê que, com gasto $5.57, cap $6 ainda fica
  em warn e a folga real começa em ~$7 (achado do product-manager).
- **Remover cap** é botão/ação separada com confirmação explícita
  ("remover o teto deixa o workspace sem freio de custo — confirmar?");
  nunca submit de campo vazio.
- Sem `any`; tipos em `frontend-ops/src/lib/types.ts`; padrão de fetch de
  `users/user-actions.tsx`.

### 4. Runbook

[RUNBOOK.md §7](../../../reference/RUNBOOK.md): "desbloquear budget LLM =
editar cap na UI ops (métricas → Custo LLM); `Remover cap` = sem teto;
janela reseta na virada do mês-calendário UTC". Substitui a receita SQL.

## Critérios de aceite (gate de merge)

1. PATCH rejeita: negativo, NaN, `> MAX_SETTABLE_BUDGET_USD`, e `NULL`
   sem `remove_cap=True` — 4 testes de reject + happy path + workspace
   inexistente (404).
2. Edição gera `AuditRecord` com `previous`/`current`/`remove_cap`
   literais (asserção em teste); operação falha se `append_audit` falhar
   (teste com sink quebrado).
3. Evento `mathoms.internal_ops.budget_change` emitido (assert em log
   capture); WARNING de salto quando `current > 3 × previous`.
4. Teste confirma que o PATCH **não** toca o cache Redis de gasto e que o
   `check_budget()` seguinte usa o cap novo (lido fresh do DB).
5. Leitura da UI usa mês-calendário UTC (mesma janela do hard-stop), não
   rolling 30d — teste fixa a paridade com `_current_month_window`.
6. `make update-openapi-snapshot` commitado; suíte backend + `npm run
   build` + `tsc --noEmit` do frontend-ops verdes.
7. Runbook atualizado. **Concluído = PR mergeado em `main` (squash) com CI
   verde.**

## Testes — comandos

```bash
pytest backend/tests/internal_ops backend/tests/api/admin -q
pytest backend/tests -q
cd frontend-ops && npm run build && npx tsc --noEmit
```

## Arquivos load-bearing

| Arquivo | Papel |
|---|---|
| `backend/app/services/internal_ops/update_workspace_business_profile.py` | Molde de service + audit |
| `backend/app/services/internal_ops/audit.py` | `append_audit`, `AuditRecord`, `_FORBIDDEN_KEYS` |
| `backend/app/services/internal_ops/results.py` | `OpResult` |
| `backend/app/api/admin/workspaces.py` | Router admin (padrão GET/PATCH business-profile) |
| `backend/app/api/admin/metrics.py` | `llm_cost_by_workspace` (janela rolling — não reusar às cegas) |
| `backend/app/services/llm_budget_service.py` | `_load_budget` fresh, `_current_month_window`, ratios 80/110 |
| `backend/app/models/workspace.py` | `monthly_llm_budget_usd` (Numeric, nullable) |
| `frontend-ops/src/app/(admin)/metrics/page.tsx` | Página que ganha a seção + ação de edição |

## Débitos registrados (não bloqueiam)

- Audit em JSONL append-only (arquivo): quando **7B.5** mover audit para
  tabela `audit_entries`, o evento `workspace.update_llm_budget` migra
  junto (sink trocável por design).
- `MAX_SETTABLE_BUDGET_USD` inicial (US$ 1.000) é chute conservador —
  calibrar com custo-alvo por workspace (`financial-planner` /
  `product-manager`) quando houver pricing.
