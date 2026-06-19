---
id: ADR-030-WS
type: adr
title: "WebSocket + polling fallback"
status: Decidido
phase: "F5"
date: "2026-04-15"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 030-WS"]
tags:
  - type/adr
  - status/decidido
size_lines: 12
---

# ADR-030-WS — WebSocket + polling fallback

**Status:** Decidido (F5)

**Decisão:** WebSocket principal com polling fallback automático (compat F2).

**Consequências:**
- ✅ Real-time em navegadores modernos
- ✅ Funciona atrás de proxies que bloqueiam WS
- ✅ Backward compatibility com polling
