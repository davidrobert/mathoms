---
id: A22.l3
type: lane
title: "Fallback needs_review atômico (LLM down → relatório não quebra)"
sprint: A22
plan: PLAN-launch-trust
status: shipped
priority: P0
branch_slug: a22-l3-fallback-needs-review-atomico
depends_on: []
parallel_with:
  - "[[A22.l1]]"
  - "[[A22.l5]]"
tags:
  - type/lane
  - sprint/a22
  - status/shipped
  - priority/p0
  - area/llm
---

# A22.l3 — Fallback needs_review atômico

> **Plano:** [[PLAN-launch-trust]] · Frente 3 (F3-O2) · **gate de KR8**.
> Independente — arranca no dia 1.

## Objetivo

Garantir que, quando o LLM cai (timeout, erro de provider, validação reprovada
por [[A22.l2]]), o relatório **renderiza sem o Parecer** com aviso de
`needs_review`, em vez de quebrar (erro 500 / página em branco).

## Escopo

- Degradação atômica no orchestrator do Parecer
  (`backend/app/services/parecer_orchestrator.py`) + renderer React.
- Estado `needs_review` propaga até a UI; relatório mostra as seções
  determinísticas (E5) intactas + banner de "parecer indisponível".
- Sem efeito colateral parcial (atômico: ou Parecer completo, ou ausência
  limpa — nunca meio-Parecer).

## Critério de aceite

- 1 teste E2E verde: LLM down → relatório renderiza sem o Parecer, sem 500.
- Teste de regressão: validação reprovada (red line de [[A22.l2]]) → mesmo
  caminho de fallback.

## Notas

- Owner: `senior-cto`.
- Abre ADR só se mudar o contrato de stage do Parecer (ADR-199); degradação
  dentro do contrato existente não exige ADR nova.
- Federa F3-O2 do plano dono.
