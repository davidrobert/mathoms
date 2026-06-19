---
id: ADR-014
type: adr
title: "Threading para execução background"
status: Decidido
phase: "F2"
date: "2026-04-15"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 014"]
tags:
  - area/backend
  - status/decidido
  - type/adr
size_lines: 11
---

# ADR-014 — Threading para execução background

**Status:** Decidido (F2) → Substituído por Celery em [D29-TQ](#adr-029-tq--celery--redis)

**Decisão original:** `threading.Thread` daemon para pipeline execution.

**Por que foi substituído:** Threads não sobrevivem a restart do servidor. Celery resolve isso + permite workers múltiplos.

**Fallback:** Celery mantém thread fallback se Redis indisponível.
