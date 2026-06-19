---
id: ADR-056
type: adr
title: "Rolling restart em vez de blue-green"
status: Decidido
phase: "F7"
date: "2026-04-15"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 056"]
tags:
  - area/ops
  - status/decidido
  - type/adr
size_lines: 9
---

# ADR-056 — Rolling restart em vez de blue-green

**Status:** Decidido (F7)

**Decisão:** `docker compose pull && up -d` com health check pós-deploy + rollback automático.

**Rationale:** Blue-green real requer 2 VPS (overkill para dogfood). Downtime <30s é aceitável.
