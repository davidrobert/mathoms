---
id: ADR-057
type: adr
title: "JWT 15min + refresh 7d"
status: Decidido
phase: "F7"
date: "1970-01-01"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 057"]
tags:
  - type/adr
  - status/decidido
size_lines: 9
---

# ADR-057 — JWT 15min + refresh 7d

**Status:** Decidido (F7)

**Decisão:** JWT access token 15min + refresh token 7d httpOnly cookie. Frontend interceptor com retry queue para 401.

**Rationale:** Reduz superfície de ataque (access token expira rápido) sem fricção (refresh automático).
