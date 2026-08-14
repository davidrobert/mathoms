---
id: A43.l8
type: lane
title: "Certificação ChatGPT/Codex, matriz adversarial e kill switch"
sprint: A43
plan: PLAN-competitive-pierre
status: planned
priority: P0
branch_slug: a43-l8-certificacao-cross-surface-e-kill-switch
depends_on: ["[[A43.l6]]", "[[A43.l7]]"]
tags: [type/lane, sprint/a43, status/planned, priority/p0, area/quality, area/security, area/product]
---

# A43.l8 — Certificação cross-surface e kill switch

> **Origem:** [[A43]] · [[PLAN-competitive-pierre]].

## Decisão

Executar o corpus da [[A43.l3]] no ChatGPT e no Codex, em sessões novas, com dois
reports/runs e dois tenants PII-zero. Avaliar separadamente tool/DTO determinístico
e seleção/resposta host-level.

## Critério de aceite

- OAuth + primeiro resultado em 2/2 superfícies, sem token/JSON manual.
- ≥9/10 tarefas corretas por superfície; 100% das suportadas com fonte e `as_of`.
- Matriz negativa do gate da [[A43]] completa; zero cross-tenant/PII.
- Trocar o report corrente muda resposta sem rebuild/reinstall.
- Injection não muda tool/scope/workspace nem amplia DTO.
- Soak mede success/p95; rate limit/timeout/cancellation têm resposta recuperável.
- Kill switch global/per-workspace exercitado; app/pipeline continuam verdes.
- Evidence pack PII-zero versiona plugin/MCP/SDK e casos. Saída: private beta ready.
