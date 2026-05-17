---
id: ADR-178
type: adr
title: "`Risk` aggregate workspace-scoped"
status: Decidido
phase: "Sprint A10.4"
date: "2026-05-06"
relates_to: ["[[ADR-090]]", "[[ADR-101]]", "[[ADR-115]]", "[[ADR-136]]", "[[ADR-143]]", "[[ADR-192]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 178"]
tags:
  - area/backend
  - area/multitenancy
  - area/persistence
  - methodology/cerbasi
  - status/decidido
  - type/adr
size_lines: 60
---

# ADR-178 — `Risk` aggregate workspace-scoped

**Status:** Decidido (Sprint A10.4) • **Data:** 2026-05-06 • **Data de decisão:** 2026-05-07 • **Relaciona** [ADR-090](#adr-090--decimal-para-valores-monetários), [ADR-101](#adr-101--princípios-r12-r17-dddsolid-no-backend-api-a6e), [ADR-115](#adr-115--domain-events-tipados-arquitetura-e-boundaries-a6eevents), [ADR-136](#adr-136--decision-aggregate-event-sourced-com-supersede-chain), [ADR-143](#adr-143--docsmethodology-é-rules-as-code-sprint-a76). **Origem:** Sprint A10 W0 — [archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md §3.4](../archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md).

**Contexto:** O bubble chart S9 ("Riscos Prioritários") do relatório premium hoje renderiza 8 dicts hardcoded prob×impacto vindos de `goals_cfg["riscos_prioritarios"]` (chave do `goals.json` arquivado, materializada em runtime). Não há aggregate por trás: usuário não pode editar; consultor não pode parametrizar por workspace; tenancy quebrada (workspace novo não-Ferreira-Campos vê dados alheios via seed). Conceito é distinto de `Decision` (ADR-136): Decision = ação a tomar; Risk = evento incerto. Sobreposição semântica existe ("decisão de contratar seguro" vs "risco de não ter seguro") mas direção é oposta — tratá-los como mesma entidade colapsa o link causa↔mitigação.

A literatura Cerbasi cataloga 5 riscos universais que todo provedor enfrenta — morte, invalidez, doença grave, desemprego, longevidade — todos com probabilidade variável e impacto financeiro mensurável. Para cliente piloto há também riscos específicos (concentração PJ, cambial, sucessório, iliquidez) que **não** se prestam a seed universal.

**Decisão:** Criar aggregate `Risk` workspace-scoped, paralelo a `Decision` (ADR-136). Modelo proposto:

```python
class Risk(Base):
    __tablename__ = "risks"
    id: UUID
    workspace_id: UUID  # FK → workspaces.id
    code: str            # slug estável (ex.: "morte_provedor")
    name: str
    rationale: str
    probability: Enum["baixa", "média", "alta"]   # qualitativo
    impact_level: Enum["baixo", "médio", "alto", "crítico"]
    impact_brl_cents: BigInteger | None  # ADR-090
    status: Enum["Ativo", "Mitigado", "Aceito", "Descartado"]
    mitigations_decision_ids: JSON  # array de Decision.id (link semântico)
    created_at, updated_at
```

**Seed template universal (não-cliente):** 5 riscos Cerbasi com `status="Ativo"` e `probability=null` (cliente preenche). Workspace novo recebe os 5 automaticamente. Riscos cliente-específicos são adicionados via UI pelo consultor/cliente, não seedados.

**Bubble chart S9** vira projeção: lê `Risk` aggregate ordenado por (`impact_level`, `probability`).

**Use cases canônicos (UI mínima de listagem):** `create_risk`, `update_risk`, `link_mitigation` (associa Decision como mitigação), `unlink_mitigation`, `change_status`, `archive_risk`.

**Alternativas consideradas:**

1. **Reusar `Decision` aggregate com `kind="risk"`** — colapsa duas direções semânticas (ação a tomar vs. evento incerto); supersede chain de Decision não modela "risco mitigado" naturalmente; UI mistura conceitos.
2. **Tabela CRUD pura (`risks` sem aggregate ddd)** — ok para v1, mas perde uniformidade com `Decision`; futuro `RiskEvent` (probabilidade variando ao longo do tempo) exigiria refactor. Aceitável de novo se v1 não tem demand de event-sourced.
3. **Aggregate workspace-scoped DDD-shaped (escolhida)** — paralelo a Decision, link semântico via `mitigations_decision_ids`, room para event-sourcing se demanda materializar. Pequena sobre-engenharia para v1; payback em sprints futuras quando UI rica de Risk entrar.
4. **Sem aggregate — apenas seed estático Cerbasi como `goals.json[riscos_prioritarios]` rules-as-code (ADR-143)** — perde tenancy; cliente não pode editar; consultor não parametriza por workspace.

**Trade-offs explícitos:**

- **Ganho:** tenancy correta; cliente edita seus riscos; consultor parametriza; bubble chart S9 fica funcional para qualquer workspace; `Decision` ↔ `Risk` link explícito documenta cause-effect.
- **Custo:** novo aggregate (model + repo + 6 use cases + endpoints + UI mínima + seed template + Alembic). ~2d estimados. Decisão event-sourced **não** estendida ao Risk (CRUD com `updated_at` basta para v1 — escopado como ADR-136 fez para Decision: "**escopado a este aggregate apenas**").
- **Risco:** Decision↔Risk sobreposição semântica confunde usuário. Mitigação: docstring no aggregate + copy UI explicita "Decisão = ação; Risco = evento incerto". Link via `mitigations_decision_ids` torna a relação navegável.

**Critério de aceite:**

- [ ] `backend/app/models/risk.py` com `Risk` aggregate, FK `workspace_id`, JSON `mitigations_decision_ids`.
- [ ] Alembic migration aplicada (tabela `risks` + index workspace_id).
- [ ] Repo `RiskRepository` + 6 use cases em `backend/app/application/risks/`.
- [ ] Endpoints `POST/GET/PATCH /risks` com `response_model` explícito (ADR-102 R18).
- [ ] OpenAPI snapshot regenerado (`make update-openapi-snapshot`).
- [ ] Seed template Cerbasi (5 riscos universais) em `backend/app/scripts/seed_risk_template.py` aplicado a workspaces novos.
- [ ] UI mínima de listagem em `/plano` (ou `/riscos` dedicada — TBD lane A10.4).
- [ ] Bubble chart S9 lê `Risk` via projeção; `goals_cfg["riscos_prioritarios"]` deletado em A10.6.
- [ ] Tests: `backend/tests/test_risk_aggregate.py` (~30 specs) cobrindo 6 use cases + tenancy + link com Decision.

**Plano de implementação:** [docs/archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md §3.4](../archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md) (lane A10.4).
