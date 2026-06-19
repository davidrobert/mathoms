---
id: ADR-031
type: adr
title: "Redis para queue + pub/sub"
status: Decidido
phase: "F5"
date: "2026-04-15"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 031"]
tags:
  - area/backend
  - status/decidido
  - type/adr
size_lines: 7
---

# ADR-031 — Redis para queue + pub/sub

**Status:** Decidido (F5)

**Decisão:** Redis serve como broker Celery, result backend e pub/sub (eventos WebSocket).
