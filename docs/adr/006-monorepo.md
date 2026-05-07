---
id: ADR-006
type: adr
title: "Monorepo"
status: Decidido
phase: "F0"
date: "2026-04-12"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 006"]
tags:
  - area/backend
  - status/decidido
  - type/adr
size_lines: 12
---

# ADR-006 — Monorepo

**Status:** Decidido (F0) • **Data:** 2026-04-12

**Decisão:** Monorepo único com backend/, frontend/, pipeline/, scripts/.

**Consequências:**
- ✅ Refactoring cross-layer fica fácil (modelo Python + schema TS)
- ✅ CI único
- ⚠️ Repos gigantes escalam pior
