---
id: ADR-030
type: adr
title: "Cancelamento cooperativo via `threading.Event`"
status: Decidido
phase: "F2"
date: "2026-04-15"
relates_to: []
supersedes: []
superseded_by: ["[[ADR-032]]"]
aliases: ["ADR 030"]
tags:
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 9
---

# ADR-030 — Cancelamento cooperativo via `threading.Event`

**Status:** Decidido (F2) → Substituído por [D32](#adr-032--cancel-stage-boundary)

**Decisão inicial:** Cooperative cancel via `threading.Event` entre stages.

**Evolução (F5):** Substituído por DB flag + Celery revoke. Mesmo princípio (stage-boundary).
