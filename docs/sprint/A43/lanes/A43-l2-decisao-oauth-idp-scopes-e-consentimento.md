---
id: A43.l2
type: lane
title: "Decisão build-vs-buy de OAuth/IdP, scopes e consentimento"
sprint: A43
plan: PLAN-competitive-pierre
status: planned
priority: P1
branch_slug: a43-l2-decisao-oauth-idp-scopes-e-consentimento
depends_on: []
adrs: ["[[ADR-109]]", "[[ADR-170]]"]
tags: [type/lane, sprint/a43, status/planned, priority/p1, area/auth, area/security, methodology/build-vs-buy]
---

# A43.l2 — OAuth/IdP, scopes e consentimento

> **Origem:** [[A43]] · [[PLAN-competitive-pierre]].

## Problema

O JWT interno e o refresh flow do app não formam um authorization server MCP.
Implementar discovery, registration, PKCE, audience/resource, consentimento e
revogação do zero cria risco fora do diferencial do Mathoms.

## Decisão a produzir

Comparar IdP/bridges estabelecidos e in-house. O plano de controle OAuth pode ser
adotado; autorização por membership, workspace, tier e scopes permanece Mathoms.
Contrato mínimo: authorization-code + PKCE S256, metadata, CIMD/DCR, verificação de
issuer/audience/resource/expiry, scopes `reports:read`, `decisions:read` e
`metrics:read`, consentimento legível e revogação.

## Critério de aceite

- Matriz cobre TCO 3 anos, TTM, LGPD/residency, lock-in, disponibilidade,
  CIMD/DCR, export e custo de saída.
- DPA, subprocessadores, retenção/deleção e transferência internacional são gate
  explícito antes de dado real.
- Token autoriza um workspace por grant; membership/tier são revalidados no server.
- Decisão preserva o login interno e reconcilia [[ADR-109]]/[[ADR-170]].
- Prova sintética completa discovery + PKCE sem segredo real em fixture/log.
