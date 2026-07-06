---
id: A29.l3
type: lane
title: "inbox de pendências em /documents: fila agrupada, banner de análise pausada, retomada explícita"
sprint: A29
plan: null
status: shipped
ship_pr: 803
ship_date: "2026-07-06"
priority: P1
branch_slug: review-ux-inbox
adrs: ["[[ADR-308]]"]
depends_on: ["[[A29.l2]]"]
tags:
  - type/lane
  - sprint/a29
  - status/shipped
  - priority/p1
  - area/ux
---

# A29.l3 — `inbox-pendencias-documents` (frontend fila; endpoint novo dispensado)

> **Desvio de escopo registrado (execução):** o item 1 (endpoint novo) foi
> dispensado — a fila compõe `GET /pipeline/runs` + `GET /runs/{id}/reviews`
> existentes, com as amostras vindas de `validation_issues` (A29.l2). Endpoint
> dedicado sobre `review_reasons` permanece follow-up da [[ADR-272]] para o
> console interno, onde a agregação consolidada é o caso de uso real. Menos um
> contrato duplicado (coerente com ADR-272 §Unificação).

## Problema

A remediação real de pendências de ingestão (atribuir instituição,
reclassificar) mora em `/documents`, mas nada conecta o run pausado à fila: o
deep-link da A28.l9 cai num toggle plano, e a tela de review não aponta para
lá. Duas superfícies de "algo precisa de você" sem taxonomia comum.

## Escopo

1. **Endpoint user-facing** de pendências agrupadas do workspace (follow-up
   órfão da [[ADR-272]]): reviews `pending` + `review_reasons` por code com
   `occurrence_count`, amostra de documentos e `document_id` linkável.
   `response_model` explícito + OpenAPI snapshot (ADR-102 R18).
2. **`PendingReviewQueue`** em `/documents`, acima da tabela: card por tipo de
   pendência (ícone + título + Badge contador), consequência em 1 frase,
   amostra 3-4 docs + "e mais N" expansível, ação individual via
   `EditDocumentDialog` existente + fluxo sequencial "N de M" para lote
   ([[ADR-308]] §8 — nunca valor único em massa; resultado parcial explícito).
3. **Banner "análise pausada"** (`Alert`, mesmo componente do A28.l9): *"Sua
   análise está pausada esperando você"* + CTA que ancora na fila; quando
   `blocking_count == 0`, muda para "Tudo resolvido — retomar agora" com CTA
   único de retomada explícita ([[ADR-308]] §6).
4. **Deep-link `?filter=needs_review`** passa a aterrissar na fila agrupada
   (query param preservada — link da A28.l9 não quebra).
5. **Des-jargonização residual**: `ReadyToResumeCard` ("Retomar pipeline" →
   "Retomar análise"); copy do 409 na tela de review ("já foi processada" →
   neutra para resolução vinda de outra superfície).
6. **Taxonomia única**: títulos/consequências dos tipos de pendência saem de
   source-of-truth único compartilhado com a tela de review e o banner do
   relatório ([[ADR-308]] §7).

## Critério de aceite

- Fila renderiza grupos ordenados por severidade e `occurrence_count`;
  contagem acima do cap exibe "50+", nunca número exato inventado.
- Reason sem `document_id` degrada para texto não-clicável (nunca link
  quebrado).
- Ação em lote com falha parcial mostra `X resolvidos, Y ainda precisam de
  você` e mantém os Y no card.
- Resolver pendências não re-dispara o run; banner flip para "retomar agora"
  (teste E2E do fluxo pausa → correção → retomada).
- `make update-openapi-snapshot` commitado; testes backend do endpoint
  (SQLite in-memory, nunca mock de DB).
- PR mergeado em `main` com CI verde.
