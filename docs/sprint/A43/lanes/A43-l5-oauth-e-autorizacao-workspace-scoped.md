---
id: A43.l5
type: lane
title: "OAuth 2.1 e autorização workspace-scoped com revogação"
sprint: A43
plan: PLAN-competitive-pierre
status: planned
priority: P0
branch_slug: a43-l5-oauth-e-autorizacao-workspace-scoped
depends_on: ["[[A43.l2]]", "[[A43.l4]]"]
adrs: ["[[ADR-109]]", "[[ADR-170]]", "[[ADR-111]]"]
tags: [type/lane, sprint/a43, status/planned, priority/p0, area/auth, area/multitenancy, area/security]
---

# A43.l5 — OAuth e autorização por workspace

> **Origem:** [[A43]] · [[PLAN-competitive-pierre]].

## Decisão

Integrar o IdP/bridge e criar authorization context imutável. Toda chamada valida
token e calcula `subject × scopes × workspace grant × membership atual × entitlement`.
Grant/revogação vivem em store durável; erros não revelam existência de recurso.

## Critério de aceite

- Discovery + authorization-code + PKCE S256 completam; issuer/audience/resource/
  expiry/scopes são verificados por request.
- Matriz 2 users × 2 workspaces cobre membership, role, scope, workspace swap e
  report cross-tenant; zero acesso indevido.
- Expired/revoked token, logout, membership removida e tier inativo mordem na
  chamada seguinte dentro do SLA documentado.
- Replay, redirect inválida, PKCE errado e audience errada são rejeitados.
- Testes usam DB real com parents de FK; nenhum mock de DB.
- Nenhum token/code/verifier/claim sensível em log; revogação global é exercitada.
