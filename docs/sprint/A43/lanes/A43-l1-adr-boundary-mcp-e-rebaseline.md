---
id: A43.l1
type: lane
title: "ADR do boundary MCP, ameaça reversa e rebaseline do plano"
sprint: A43
plan: PLAN-competitive-pierre
status: planned
priority: P1
branch_slug: a43-l1-adr-boundary-mcp-e-rebaseline
depends_on: []
adrs: ["[[ADR-108]]", "[[ADR-109]]", "[[ADR-111]]", "[[ADR-175]]"]
tags: [type/lane, sprint/a43, status/planned, priority/p1, area/architecture, area/security, area/ai-platform]
---

# A43.l1 — ADR do boundary MCP, ameaça reversa e rebaseline

> **Origem:** [[A43]] · [[PLAN-competitive-pierre]].

## Problema

O plano antigo descreve Mathoms-as-MCP, mas não materializa a decisão e protege
principalmente o fluxo Mathoms → LLM. MCP abre o fluxo inverso: um host/modelo
externo pede que Mathoms leia dados privados. Essa trust boundary não pode ser
decidida dentro do PR do servidor.

## Decisão a produzir

Criar ADR `Proposto`, com ID alocado somente na escrita, decidindo endpoint e
transporte, ASGI/deployment separado, core MCP vendor-neutral, application ports,
estado durável, threat model, feature flag/kill switch e plano de saída. Proibir DB
ad hoc, loopback HTTP e imports de `pipeline/**`. Rebaselinar o plano na mesma lane.

## Critério de aceite

- ADR mergeada antes do primeiro PR produtivo P1/P0.
- Alternativas “não integrar”, OpenAI-first e híbrida têm TCO/lock-in/saída; a
  recomendação inicial híbrida é confirmada ou rejeitada com evidência.
- Diagrama mostra sujeito, cliente, authorization server, MCP, application service,
  repository e audit sink.
- Threat model cobre confused deputy, tool poisoning, injection, replay, token
  theft, workspace swap, oversized result e exfiltration.
- [[ADR-108]] é emendada/supersedida para decidir a URL; sem hostname por fiat.
- [[PLAN-competitive-pierre]] e os gates documentais ficam sincronizados.
