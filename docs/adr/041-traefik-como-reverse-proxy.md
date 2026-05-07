---
id: ADR-041
type: adr
title: "Traefik como reverse proxy"
status: Decidido
phase: "F7"
date: "1970-01-01"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 041"]
tags:
  - area/ops
  - status/decidido
  - type/adr
size_lines: 9
---

# ADR-041 — Traefik como reverse proxy

**Status:** Decidido (F7)

**Decisão:** Traefik v3 (Docker-native, auto-SSL via Let's Encrypt, labels-based routing).

Alternativas descartadas: nginx (config manual), Caddy (ecossistema menor).
