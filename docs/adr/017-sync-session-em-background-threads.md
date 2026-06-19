---
id: ADR-017
type: adr
title: "Sync session em background threads"
status: Decidido
phase: "F2"
date: "2026-04-15"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 017"]
tags:
  - area/auth
  - area/backend
  - status/decidido
  - type/adr
size_lines: 7
---

# ADR-017 — Sync session em background threads

**Status:** Decidido (F2)

**Decisão:** Pipeline é 100% código sync. Usar `SessionLocal` (sync) em threads/tasks de background. AsyncSession requer event loop complexo.
