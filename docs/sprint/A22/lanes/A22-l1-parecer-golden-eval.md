---
id: A22.l1
type: lane
title: "24 golden fixtures do Parecer + métrica de eval em CI"
sprint: A22
plan: PLAN-launch-trust
status: open
priority: P0
branch_slug: a22-l1-parecer-golden-eval
depends_on: []
parallel_with:
  - "[[A22.l3]]"
  - "[[A22.l5]]"
tags:
  - type/lane
  - sprint/a22
  - status/open
  - priority/p0
  - area/llm
---

# A22.l1 — 24 golden fixtures do Parecer + eval em CI

> **Plano:** [[PLAN-launch-trust]] · Frente 3 (F3-O0) · **gate de KR7 (parcial)**.
> Pré-requisito duro de [[A22.l2]] (validação) e [[A22.l4]] (drift).

## Objetivo

Construir o harness de eval do Parecer do Planejador com **24 fixtures
sintéticas zero-PII** e rodá-lo em CI, estabelecendo o baseline que as demais
lanes de F3 consomem.

## Escopo

- 24 goldens cobrindo casos felizes **e** adversariais: input contraditório,
  tentativa de injeção (reaproveitar vetores de [[ADR-175]] / A21.l6), dado
  faltante, números no limite de threshold de domínio.
- Métrica de eval em CI: cobertura de seções, taxa de `needs_review`, e o
  scaffold onde [[A22.l2]] pluga as 7 red lines.
- **Goldens mockados no PR** (determinístico, rápido, sem chamada de provider).
  LLM-real nightly fica como Should (depende de orçamento de provider).

## Critério de aceite

- 24/24 fixtures em `tests/` (zero-PII: CPF com dígito verificador inválido,
  valores fictícios), eval roda verde em CI.
- Harness reutilizável por l2/l4 (não acoplar a red lines ainda).
- Determinístico (temperatura/seed pinados no mock).

## Notas

- Owner: `prompt-engineer`.
- Sem ADR (usa padrão de golden de execução já existente no repo).
- Federa F3-O0 do plano dono — checkbox flippa no merge.
