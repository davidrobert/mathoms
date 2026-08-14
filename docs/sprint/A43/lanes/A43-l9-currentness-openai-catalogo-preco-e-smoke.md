---
id: A43.l9
type: lane
title: "Currentness OpenAI: catálogo, preço, smoke e política de upgrade"
sprint: A43
plan: PLAN-competitive-pierre
status: planned
priority: P2
branch_slug: a43-l9-currentness-openai-catalogo-preco-e-smoke
depends_on: []
adrs: ["[[ADR-024]]", "[[ADR-025]]", "[[ADR-026]]", "[[ADR-173]]", "[[ADR-289]]"]
tags: [type/lane, sprint/a43, status/planned, priority/p2, area/llm, area/quality]
---

# A43.l9 — Currentness OpenAI

> **Origem:** [[A43]] · [[PLAN-competitive-pierre]].

## Problema

O provider existe, mas catálogo/preços/smoke não provam a família corrente. Isso
sustenta “adapter compatível”, não “integração certificada”. É independente do MCP.

## Decisão

Atualizar catálogo/pricing pela documentação oficial vigente no PR, com model/version
explícito. Smoke real cobre structured output, parameters, tokens/custo e erros.
Preservar LiteLLM/multi-provider; Responses API só entra em decisão de novo workflow.

## Critério de aceite

- Família corrente disponível entra sem substituir silenciosamente escolha antiga
  nem aliasar `latest` em produção.
- Pricing tem fonte/data e teste catálogo↔preço; ausência falha cedo ou é explícita.
- Smoke real valida Pydantic output, usage/custo, timeout e erro; secret ausente não
  produz falso-verde.
- Default não muda sem eval/custo/latência e revisão `prompt-engineer`.
- Política de cadence, pin/deprecation e rollback; cross-provider permanece verde.
