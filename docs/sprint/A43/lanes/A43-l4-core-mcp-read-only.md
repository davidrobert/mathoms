---
id: A43.l4
type: lane
title: "Core MCP remoto read-only sobre application ports"
sprint: A43
plan: PLAN-competitive-pierre
status: planned
priority: P1
branch_slug: a43-l4-core-mcp-read-only
depends_on: ["[[A43.l3]]"]
adrs: ["[[ADR-111]]"]
tags: [type/lane, sprint/a43, status/planned, priority/p1, area/backend, area/ai-platform]
---

# A43.l4 — Core MCP remoto read-only

> **Origem:** [[A43]] · [[PLAN-competitive-pierre]].

## Decisão

Implementar servidor remoto com SDK pinado, entrypoint ASGI próprio e deployment
separado. O adapter recebe use cases por injeção e retorna somente DTOs da
[[A43.l3]]. Tools: resumo atual, decisões ativas e explicação de métrica; locator
paginado entra só se necessário. Todas são read-only e orientadas ao job.

## Critério de aceite

- HTTPS/Streamable HTTP passa initialize, list tools e calls no MCP Inspector.
- Nenhum módulo MCP importa repository concreto, `pipeline/**` ou router FastAPI.
- Tool não aceita `workspace_id` como autoridade; auth context é injetado.
- Contract tests congelam names, schemas, annotations e error mapping.
- Caps, timeout, cancellation, input inválido e backend unavailable são testados.
- SDK pinado; servidor stateless funciona em ≥2 workers.
- Com feature flag off, app/API/pipeline passam sem importar MCP.
