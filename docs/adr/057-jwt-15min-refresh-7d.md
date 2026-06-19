---
id: ADR-057
type: adr
title: "JWT 15min + refresh 7d"
status: Decidido
phase: "F7"
date: "2026-04-15"
relates_to: []
supersedes: []
superseded_by: ["[[ADR-170]]"]
aliases: ["ADR 057"]
tags:
  - area/auth
  - status/decidido
  - type/adr
size_lines: 9
---

# ADR-057 — JWT 15min + refresh 7d

**Status:** Decidido (F7)

**Decisão:** JWT access token 15min + refresh token 7d httpOnly cookie. Frontend interceptor com retry queue para 401.

**Rationale:** Reduz superfície de ataque (access token expira rápido) sem fricção (refresh automático).

> **Nota (2026-06-09):** decidida em F7 mas implementada só pela metade —
> o backend emitia apenas access token com TTL 24h. O gap foi re-identificado
> como finding SR-002 (PLATFORM_REVIEW) e entregue por [[ADR-170]]
> (W3-T03), que supersede esta ADR.
