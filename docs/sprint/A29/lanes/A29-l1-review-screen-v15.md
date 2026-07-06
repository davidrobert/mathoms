---
id: A29.l1
type: lane
title: "tela de review v1.5: agrupamento, consequência explícita e telemetria review_action"
sprint: A29
plan: null
status: in_progress
priority: P0
branch_slug: review-ux-inbox
adrs: ["[[ADR-308]]"]
depends_on: []
tags:
  - type/lane
  - sprint/a29
  - status/in-progress
  - priority/p0
  - area/ux
---

# A29.l1 — `review-screen-v15` (frontend + telemetria · sem mudança de contrato)

## Problema

Caso real (run `c3d37532`, review `3811515a`): 18 erros legacy duplicados sem
documento, JSON 29KB como superfície primária, botão primário "Aprovar como
está" sem consequência. O owner aprovou às cegas — anti-padrão que o KR1 mede.

## Escopo

1. **`GroupedIssuesList`** substitui a lista plana em
   `ValidationErrorsPanel.tsx`: grupos por `code` (ponte para dados legacy:
   agrupar por `legacy_message`/linha normalizada), contador em pill,
   descrição única por grupo, ≤5 ocorrências visíveis + "e mais N".
   Erros antes de avisos; `<details>` aberto se ≤2 grupos.
2. **Hierarquia de ações** (`ReviewActions.tsx`): primário "Editar e
   continuar"; secundário outline "Continuar sem estes N documentos" com
   consequência sempre visível (*"Estes N documentos ficam de fora do
   relatório. Você pode enviá-los corrigidos depois."*) associada via
   `aria-describedby`; `ConfirmDialog` quando há erros; toasts por ação.
3. **Layout 1 coluna** (`[reviewId]/page.tsx`): lista de conferência
   full-width no topo; `JsonViewer` desce para `<details>` "Ver dados
   extraídos (avançado)" fechado; "Ir para o campo" abre o details antes do
   scroll + move foco.
4. **h1 orientado a tarefa** (`ReviewDetailHeader.tsx`): "Conferir N itens
   antes de continuar"; zero stage/output/pipeline fora de "Detalhes
   técnicos".
5. **Telemetria `review_action`**: log estruturado server-side no submit do
   review (`approve_as_is | ignore_docs | edit`, com `error_count`), namespace
   `mathoms.*` — instrumenta o KR1 sem tabela nova.
6. **Baseline KR2**: query em `review_reasons` num run limpo pós-A28.l8,
   registrada no PR.

## Critério de aceite

- Fixture com os 18 erros reais renderiza ≤ nº de mensagens distintas em
  grupos, zero texto duplicado (Vitest).
- Ação primária não é aprovar; consequência visível sem hover (teste de
  componente).
- Screen reader: summary de grupo anuncia título + contagem + severidade;
  nenhum texto idêntico lido >1×.
- Evento `review_action` emitido em cada resolução (teste backend).
- PR mergeado em `main` com CI verde.
