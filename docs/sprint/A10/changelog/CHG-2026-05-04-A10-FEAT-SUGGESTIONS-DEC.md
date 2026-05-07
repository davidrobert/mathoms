---
id: CHG-2026-05-04-A10-FEAT-SUGGESTIONS-DEC
type: changelog-entry
date: "2026-05-04"
sprint: A10
adrs: ["[[ADR-161]]", "[[ADR-162]]", "[[ADR-163]]"]
prs: [5, 6]
commits: ["d9e0f1a2b3c4", "e0f1a2b3c4d5"]
summary: |
  feat(suggestions+decisions): Onda 8 — coerência metodológica (2026-05-04). - **feat(suggestions+decisions): Onda 8 — coerência metodológica (2026-05-04):** Fecha 6 gaps identificados na revisão de produto 2026-04-29: - **#1 (ADR-161):*
tags:
  - type/changelog-entry
  - sprint/a10
---


# feat(suggestions+decisions): Onda 8 — coerência metodológica (2026-05-04)

- **feat(suggestions+decisions): Onda 8 — coerência metodológica (2026-05-04):**
  Fecha 6 gaps identificados na revisão de produto 2026-04-29:
  - **#1 (ADR-161):** 6 regras canônicas v2 no `SuggestionGenerator`
    (Cerbasi/AUVP/Perini completos): `endividamento_perigoso` (danger),
    `taxa_poupanca_caindo` (warning · comportamental), `seguros_insuficientes`
    (danger · proteção), `concentracao_instituicao` (warning · AUVP),
    `lifestyle_creep` (warning · comportamental), `renda_passiva_real_baixa`
    (info · Perini "300"). `SUGGESTION_CAP` sobe 6→8. Campo `category`
    auto-derivado (alvo_if/carteira/protecao/comportamental/endividamento/
    usa_plano). Refactor: rules → `suggestion_rules.py`, config →
    `suggestion_config.py`. Onda 10 #5 enrichments preservados (rationale
    com gap+ETA em reserva e atual/alvo/tabela em alocação). Migration
    aditiva `d9e0f1a2b3c4`. 43 testes verdes (39 v2 + 4 Onda 10).
  - **#2 (ADR-162):** Decisions atualizam Goals via event projection.
    Campos novos: `target_field`, `target_value`, `target_value_type`.
    Tabela `PROJECTIONS` em `backend/app/services/decision_goal_projection.py`
    mapeia 6 paths (goal.if.*, goal.aporte.*, goal.dolar.*).
    `mark_decision_executed` dispara `project_decision_to_goal` na mesma
    transação; falha → ValidationError + rollback. Goal nova carrega
    `notes="Derivada da Decision <code>"` e DecisionEvent `GoalProjected`
    com `goal_id`. 6 testes novos.
  - **#3:** DecisionCard ganha botão "Gerar tarefas" (status Decidido|Executado);
    `GenerateTasksDialog` pré-popula 1-3 templates por `target_field` (goal.if
    → "Atualizar planilha de IF" + "Reler relatório com novo TRS"; etc.).
    Cada Task criada carrega `derived_from_decision_id` (FK→decisions,
    migration `g3b4c5d6e7f8`). UI: lista editável antes de salvar.
  - **#4:** SuggestionCard aplica `border-l-4` colorida por severidade
    (antes definida em `SEVERITY_CONFIG.cls` mas nunca chegava ao Card).
    InboxTab ordena por `suggestionSortComparator` (severity desc →
    created_at desc). 3 testes novos.
  - **#5:** `/suggestions/summary` novo endpoint (count + max_severity +
    by_category). `useSuggestionsSummary` substitui `useSuggestionsCount`
    em /plano. SuggestionsBanner colore por max_severity (danger=vermelho,
    warning=amarelo, info=azul) — antes escalava por volume, mostrando
    banner azul calmo para 1 sugestão `danger`. Bug semântico fechado.
  - **#6 (ADR-163):** Decision congela `context_snapshot` (JSON nullable)
    ao aceitar Suggestion: 5 campos (`patrimonio_brl`, `if_progress_pct`,
    `trs_pct_when_decided`, `report_id`, `report_period`) lidos do
    relatório-fonte via `report_id`. DecisionCard exibe "Decidida com
    base em: ..." quando snapshot presente. Migration única
    `e0f1a2b3c4d5` para campos #2 + #6.

  Total: 3 ADRs novas (161/162/163), 3 migrations. 1586 backend tests +
  1661 pipeline tests + 739+ frontend tests verdes. OpenAPI snapshot
  atualizado.

- **feat(ui): Onda 10 — coerência cross-rota /plano · /reports · /acao
  (2026-05-04):** 6 fixes UI fecham os gaps de navegação entre as 3 telas
  críticas do ritual mensal do casal usuário identificados na revisão
  multi-agente (`product-designer` 2026-05-04).
  1. `<MonetaryValue/>` ganha prop `size={"hero"|"kpi"|"body"}` que aplica
     `text-style-hero` / `text-style-kpi-value` do design-tokens.
     `<IFHeroCard/>` Patrimônio migra para `size="hero"` — chega à mesma
     fonte do `<HeroKpiGrid/>` em /reports. Demais `formatCurrency()` em
     JSX dentro de `(app)/plano/_components/**` substituídos por
     `<MonetaryValue/>` (zero ofensores no grep gate).
  2. CTA primário "Abrir relatório de {mês}" via `<ReportLinkAction/>`
     nas actions do `<PageHeader/>` de /plano. Workspace sem Report → CTA
     outline "Gerar relatório" → /documents. Cada KPI da `<PlanoKpiRow/>`
     vira `<Link>` para a seção do relatório que aprofunda o número
     (Patrimônio → §S1, IF → §S7, Aporte → §S2).
  3. `<SuggestionReportLink/>` adiciona backward link "Ver no relatório
     do mês · §{section_id}" no card da Inbox em /acao — fecha o ciclo
     forward (Onda 7 #3) ↔ backward. Dialogs (Accept/Modify/Dismiss)
     extraídos para `SuggestionDialogs.tsx` para manter `SuggestionCard.tsx`
     ≤500 linhas.
  4. `<SuggestionCallout/>` migra de Tailwind utilities (`border-l-sky-500`,
     `bg-amber-50`, `text-red-900`) para tokens semânticos
     `var(--semantic-info-financial | --semantic-alert | --semantic-loss)`
     com `color-mix(in oklab, ...)`. Dark mode resolve automaticamente
     pelo `tokens.css`.
  5. `suggestion_generator.py` enriquece `rationale` das regras 2
     (reserva insuficiente) e 3 (alocação fora do alvo): gap em BRL +
     ETA com aporte mensal projetado (regra 2); atual/alvo/Δ + tabela
     markdown de classes + sugestão de próximo aporte (regra 3). Helper
     `_format_brl()` formata Decimal em padrão BR sem locale do sistema.
     Defensivo — degrada para versão curta se snapshot incompleto.
     Cobertura: 4 testes novos em `tests/test_suggestion_generator.py`
     (24 total, todos verdes).
  6. /acao em workspace zero (pending+tasks+notes = 0) cai em
     `<EmptyState/>` apontando para /plano (entrada canônica do
     `<OnboardingHero/>`). Hook novo `useAcaoZeroSignals(workspaceId)`
     compõe os 3 sinais.
  Track: [docs/agent_prompts/track_onda_10_cross_route_coherence.md](agent_prompts/track_onda_10_cross_route_coherence.md).
