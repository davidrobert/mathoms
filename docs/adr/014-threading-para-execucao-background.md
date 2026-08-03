---
id: ADR-014
type: adr
title: "Threading para execução background"
status: Decidido
phase: "F2"
date: "2026-04-15"
relates_to: []
supersedes: []
superseded_by: ["[[ADR-029-TQ]]", "[[ADR-359]]"]
aliases: ["ADR 014"]
tags:
  - area/backend
  - status/decidido
  - type/adr
size_lines: 11
---

# ADR-014 — Threading para execução background

> A cláusula de fallback abaixo sobreviveu à substituição por Celery e manteve
> um `threading.Thread(daemon=True)` vivo em `pipeline_service` até 2026-08-03,
> quando [[ADR-359]] a removeu. Corpo preservado como registro histórico.

**Status:** Decidido (F2) → Substituído por Celery em [D29-TQ](#adr-029-tq--celery--redis)

**Decisão original:** `threading.Thread` daemon para pipeline execution.

**Por que foi substituído:** Threads não sobrevivem a restart do servidor. Celery resolve isso + permite workers múltiplos.

**Fallback:** Celery mantém thread fallback se Redis indisponível.
