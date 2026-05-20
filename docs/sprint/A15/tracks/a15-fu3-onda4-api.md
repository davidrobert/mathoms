---
id: TRACK-a15-fu3-onda4-api
type: track
title: "Track A15 FU-3 Onda 4 — API endpoints + OpenAPI snapshot"
sprint: A15
plan: PLAN-imovel-financiado
status: ready
created_at: "2026-05-20"
consumed_at: null
agent_role: senior-cto
tags:
  - type/track
  - sprint/a15
  - status/ready
  - area/backend
  - area/api
---

# Track A15 FU-3 Onda 4 — API endpoints + OpenAPI snapshot

> **Lane:** Sprint A15 · **Plano canônico:**
> [PLAN-imovel-financiado](../../../plan/IMOVEL_FINANCIADO/_README.md) §Onda 4
> · **ADR canônica:** [[ADR-227]] §D1 + §D2 (CRUD shape) + [[ADR-109]] (response_model + snapshot)
> · **Branch prefix:** `agent/a15-fu3-onda4-api/*`
> · **Pré-requisito externo:** Onda 1 mergeada (models + repos) + Onda 3 mergeada (adapter + warning). Pode rodar em paralelo com Onda 5 (frontend), pois UI consome endpoints daqui.
> · **Bloqueia:** Onda 5 (frontend) — UI consome endpoints.

## Briefing

Endpoints REST para CRUD de `Debt` + `PropertyMarketValue` ([[ADR-227]] §D1 + §D2). Snapshot OpenAPI atualizado ([[ADR-109]] R18 — todo endpoint JSON exige `response_model` explícito).

**7 endpoints novos:**

| Verbo | Path | Função | response_model |
|---|---|---|---|
| GET | `/v1/workspaces/{ws_id}/debts` | List Debts do workspace | `list[DebtResponse]` |
| POST | `/v1/workspaces/{ws_id}/debts` | Create Debt (manual) | `DebtResponse` (201) |
| PATCH | `/v1/debts/{debt_id}` | Update Debt (incluindo link a property_id) | `DebtResponse` |
| DELETE | `/v1/debts/{debt_id}` | Delete Debt | 204 No Content |
| GET | `/v1/workspaces/{ws_id}/property-market-values` | List values do workspace | `list[PropertyMarketValueResponse]` |
| POST | `/v1/workspaces/{ws_id}/property-market-values` | Create value (append-only) | `PropertyMarketValueResponse` (201) |
| PATCH | `/v1/property-market-values/{value_id}/supersede` | Marca valor como superseded por outro | `PropertyMarketValueResponse` |

**Endpoint adicional para batch review (Onda 5 consome):**

| Verbo | Path | Função | response_model |
|---|---|---|---|
| GET | `/v1/workspaces/{ws_id}/debts?needs_review=true` | List Debts pendentes de review (filter do endpoint base) | `list[DebtResponse]` |

**Tenancy:** todos os endpoints filtram por `workspace_id` via dependency `get_current_workspace` (pattern existente). DELETE com FK RESTRICT a property_id → response 409 com payload listando Debts bloqueantes.

## Critério de aceite (do plano §Onda 4)

- [ ] `backend/app/api/debt.py` com 4 endpoints CRUD (GET list, POST create, PATCH update, DELETE).
- [ ] `backend/app/api/property_market_value.py` com 3 endpoints (GET list, POST create, PATCH supersede).
- [ ] DTOs Pydantic em `backend/app/schemas/dto/debt/{command,response}.py` + `property_market_value/{command,response}.py` (já criados em Onda 1; estender se necessário).
- [ ] **`response_model` explícito** em todo endpoint JSON ([[ADR-109]] R18). DELETE → 204.
- [ ] Tenancy: `Depends(get_current_workspace)` em endpoints workspace-scoped.
- [ ] Validação:
  - POST Debt sem nenhuma identidade (sem `family_member_id`, `property_id`, `descricao`) → 422 (Pydantic CHECK constraint).
  - PATCH Debt setando `property_id` que não existe → 422.
  - DELETE PropertyIdentity com Debt vinculada → 409 + payload `{debts_blocking: [debt_id, ...]}`.
  - POST PropertyMarketValue com `valuation_date` já existente para mesma property → 409 (constraint UNIQUE).
  - `percentual_atribuicao_imovel` fora de (0, 100] → 422.
- [ ] PATCH `supersede` aceita `superseded_by_id` (UUID de PropertyMarketValue existente do mesmo property_id); UPDATE `superseded_by_id` no row alvo.
- [ ] Snapshot OpenAPI atualizado (`make update-openapi-snapshot` ou equivalente). `backend/tests/test_openapi_snapshot.py` verde.
- [ ] `backend/tests/test_openapi_response_models.py` verde — todo endpoint JSON tem `response_model`.
- [ ] Test integration para cada endpoint:
  - CRUD básico (create → list → patch → delete).
  - Tenancy: usuário do workspace A não vê Debts do workspace B (403/404).
  - RESTRICT: deletar PropertyIdentity vinculada → 409.
  - UNIQUE: duplicar `(property_id, valuation_date)` → 409.
  - Idempotência: PATCH supersede 2× → 2ª roda é no-op.
- [ ] `pytest backend/tests/api -q` + `pre-commit run --all-files` verdes.

## Arquivos esperados

**Novos:**

- `backend/app/api/debt.py`
- `backend/app/api/property_market_value.py`
- `backend/tests/api/test_debt_endpoints.py`
- `backend/tests/api/test_property_market_value_endpoints.py`

**Editados:**

- `backend/app/main.py` (ou wherever routers são registrados) — incluir 2 routers novos.
- `backend/openapi_snapshot.json` (auto-gerado) — snapshot atualizado.
- `backend/app/schemas/dto/debt/{command,response}.py` — estender se faltar campo (e.g. `property_id_to_set` em PATCH).

## Decisões já fechadas (do co-design 2026-05-19)

- **CRUD completo para Debt** + **append-only com supersede** para PropertyMarketValue — refletindo modelo de domínio: dívida muda (saldo amortiza), valor de mercado é declaração histórica.
- **`response_model` obrigatório** ([[ADR-109]] R18) — gate enforçado por `backend/tests/test_openapi_response_models.py`. DELETE 204 isento.
- **409 Conflict para FK RESTRICT** com payload acionável (`{debts_blocking: [...]}`) — UI (Onda 5) renderiza modal "Desvincule antes de deletar".
- **Filter `?needs_review=true`** no GET list — reuso do endpoint base em vez de endpoint dedicado. Pattern de filter já consagrado.
- **Tenancy default** via `get_current_workspace` — pattern existente; sem variação.
- **Snapshot OpenAPI commitado** com PR — gate de regressão ([[ADR-109]]).

## Testes (comandos exatos)

```bash
# Endpoints Debt
pytest backend/tests/api/test_debt_endpoints.py -v

# Endpoints PropertyMarketValue
pytest backend/tests/api/test_property_market_value_endpoints.py -v

# Response models + snapshot
pytest backend/tests/test_openapi_response_models.py -q
pytest backend/tests/test_openapi_snapshot.py -q

# Suítes completas
pytest backend/tests -q
pre-commit run --all-files

# Atualizar snapshot se mudança intencional
make update-openapi-snapshot
# verificar diff antes de commitar
```

## Riscos

- **R1** — Snapshot OpenAPI fica fora de sync se desenvolvedor esquecer `make update-openapi-snapshot`. **Mitigação:** `backend/tests/test_openapi_snapshot.py` falha em CI; documentação no PR template.
- **R2** — Endpoint `PATCH supersede` precisa validar que `superseded_by_id` aponta para PropertyMarketValue do MESMO `property_id`. **Mitigação:** validação explícita no service-layer, test integration cobre.
- **R3** — `percentual_atribuicao_imovel` em PATCH: Pydantic schema OK, mas DB CHECK constraint pode dar erro 500 se Pydantic não validar primeiro. **Mitigação:** Pydantic `Field(gt=0, le=100)` no DTO + CHECK como segunda linha.
- **R4** — Order de delete: usuário deleta Debt antes de tentar deletar PropertyIdentity. Sem isso, 409 é a única resposta. UX (Onda 5) precisa expor link "deletar Debt" no modal de erro.
- **R5** — Endpoints novos podem ser invocados antes da Onda 5 (frontend) estar pronto; chamadas raw via curl/Postman devem funcionar. **Mitigação:** test integration cobre flow end-to-end via TestClient.

## Ligações

- Plano canônico: [PLAN-imovel-financiado](../../../plan/IMOVEL_FINANCIADO/_README.md) §Onda 4
- ADR canônica: [[ADR-227]] §D1 + §D2; [[ADR-109]] (response_model + snapshot)
- Sprint MOC: [[MOC-sprint-a15]]
- Onda 1 (pré-req): [a15-fu3-onda1-schema](a15-fu3-onda1-schema.md)
- Onda 3 (pré-req paralelo): [a15-fu3-onda3-calculator](a15-fu3-onda3-calculator.md)
- Onda 5 (próximo): [a15-fu3-onda5-frontend](a15-fu3-onda5-frontend.md) — UI consome endpoints
- Pattern reuso: outros endpoints CRUD com tenancy + RESTRICT pattern (e.g. `backend/app/api/family_member.py`, `backend/app/api/category.py`)
- ADRs relacionados: [[ADR-109]] (response_model gate), [[ADR-090]] (Decimal no wire)
