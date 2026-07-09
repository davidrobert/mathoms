---
id: ADR-179
type: adr
title: "`Decision` aggregate — extensão de schema (`impact_1y/10y`, `horizon`, `priority`)"
status: Decidido
phase: "Sprint A10.3"
date: "2026-05-06"
relates_to: ["[[ADR-090]]", "[[ADR-102]]", "[[ADR-109]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 179"]
tags:
  - area/backend
  - area/money
  - area/persistence
  - status/decidido
  - type/adr
size_lines: 45
---

# ADR-179 — `Decision` aggregate — extensão de schema (`impact_1y/10y`, `horizon`, `priority`)

**Status:** Decidido (Sprint A10.3) • **Data:** 2026-05-06 • **Data de decisão:** 2026-05-07 • **Estende** [ADR-136](#adr-136--decision-aggregate-event-sourced-com-supersede-chain) • **Relaciona** [ADR-090](#adr-090--decimal-para-valores-monetários), [ADR-102](#adr-102--princípios-r18-r20-language-neutral-boundaries-a6f), [ADR-109](#adr-109--auth-portability-jwt-hs256--fernet-documentados-como-contratos-portáveis-a6f5a). **Origem:** Sprint A10 W0 — [archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md §3.3](../archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md).

**Contexto:** Card S10 do relatório premium ("Top 5 Decisões de Impacto") hoje renderiza string editorial Andrade-Silva vinda de `goals_cfg["top5_decisoes"]` (concatenação f-string em `charts_narrator.py:382-393`). `Decision` aggregate (ADR-136) tem aggregate event-sourced + UI `/plano` desde Sprint A7, mas o card S10 ignora — duas fontes de verdade para o mesmo conceito. Para fazer S10 consultar o aggregate via projeção (lane A10.5), faltam 4 atributos críticos: **quantificação de impacto** (1y/10y), **horizonte** temporal e **prioridade manual** do consultor.

Decision em produção tem registros com `amount_brl_cents` populado mas sem essas 4 colunas. Migration **non-breaking** com defaults sensatos é o caminho — registros existentes continuam servíveis; backfill heurístico opcional via migrator dedicado.

**Decisão:** Adicionar 4 colunas a `backend/app/models/decision.py` via Alembic non-breaking:

- `impact_1y_brl_cents: BIGINT NULL` — impacto financeiro projetado em 1 ano (ADR-090: cents).
- `impact_10y_brl_cents: BIGINT NULL` — idem 10 anos.
- `horizon: VARCHAR(16) NOT NULL DEFAULT 'short_6_12m'` — enum `{short_6_12m, medium_1_3y, long_5y_plus}`. Default permite query do card S10 sem migrator pesado para Decisions existentes.
- `priority: SMALLINT NULL` — ordenação manual do consultor; nulo ordena por `impact_1y_brl_cents DESC NULLS LAST`.

**Migrator dedicado:** `backend/app/scripts/backfill_decision_impact.py` com `--dry-run` aplica heurística — aporte mensal × 12 quando aplicável; seguro = cobertura; etc. Backfill é **opcional** — endpoint `/decisions/{id}` aceita ausência dos campos (DTO opcionais).

**DTO + UI form** atualizam para receber/exibir os 4 campos. OpenAPI snapshot regerado.

**Alternativas consideradas:**

1. **Continuar com `amount_brl_cents` único + ordenar por ele** — não diferencia "ação que paga em 1 ano" de "ação que paga em 10 anos"; consultor humano ordena diferente em horizonte curto vs. longo.
2. **Tabela paralela `decision_impact_projections` (one-to-one)** — over-normalization para 4 colunas opcionais sem múltiplas projeções por Decision. Custo de join sem ganho.
3. **Estender Decision diretamente (escolhida)** — non-breaking; defaults sensatos; backfill opcional; minimal cirurgia em DTO/repo/UI.
4. **`priority` como `kind="numeric"` event no aggregate event-sourced ADR-136** — possível mas overkill; prioridade manual do consultor não precisa de log de eventos. Aceitável de novo se UX validar uso.

**Trade-offs explícitos:**

- **Ganho:** card S10 deixa de ler string hardcoded (lane A10.5); consultor parametriza horizonte e prioridade pela UI; ordenação justificável (`impact_1y DESC` para curto prazo, `impact_10y DESC` para longo).
- **Custo:** Alembic migration + DTO + UI form + migrator backfill (~1.5d). Goldens E5/E5.N podem mudar ordenação do top 5 — risco alto de paridade (mitigado em A10.5 com PR de reset dedicado ao goldens se necessário).
- **Risco:** 3 migrations Alembic simultâneas (A10.3 + A10.4 + A10.7 na mesma onda) — heads collision. Mitigação: serializar dependência ou merge migration explícita.

**Critério de aceite:**

- [ ] Alembic migration adiciona 4 colunas a `decisions` (nullable + default `horizon='short_6_12m'`).
- [ ] DTOs `DecisionRead`, `DecisionUpdate`, `DecisionCreate` recebem os 4 campos novos (Pydantic Optional onde apropriado).
- [ ] UI form em `/plano` exibe e edita `impact_1y_brl_cents`, `impact_10y_brl_cents`, `horizon` (select), `priority` (input).
- [ ] OpenAPI snapshot regenerado (`make update-openapi-snapshot`).
- [ ] `backend/app/scripts/backfill_decision_impact.py` com `--dry-run` validado em staging antes de aplicar em prod.
- [ ] Tests `backend/tests/test_decision_extension.py` (~10 specs) cobrindo migration backward-compat, ordenação `priority NULL` → `impact_1y DESC NULLS LAST`, validação `horizon` enum.
- [ ] Endpoint `/decisions/{id}` aceita registros legados sem os 4 campos (Optional retorna null no DTO).

**Plano de implementação:** [docs/archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md §3.3](../archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md) (lane A10.3).
