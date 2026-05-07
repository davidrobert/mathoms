---
id: ADR-029-TQ
type: adr
title: "Celery + Redis"
status: Decidido
phase: "F5"
date: "1970-01-01"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 029-TQ"]
tags:
  - area/backend
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 19
---

# ADR-029-TQ — Celery + Redis

**Status:** Decidido (F5)

**Contexto:** Precisamos de task queue para pipeline assíncrono. Opções: Celery, ARQ, Dramatiq.

**Decisão:** Celery + Redis.

**Consequências:**
- ✅ Sync-native (pipeline é sync)
- ✅ Maduro, grande ecossistema
- ✅ Flower dashboard (se necessário)
- ⚠️ Mais pesado que ARQ

Alternativas descartadas:
- **ARQ:** async-native, mas pipeline é sync; sobrecarga de event loop
- **Dramatiq:** menos maduro, menor ecossistema
