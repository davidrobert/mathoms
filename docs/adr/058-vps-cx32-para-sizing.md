---
id: ADR-058
type: adr
title: "VPS CX32 para sizing"
status: Proposto
phase: "F7"
date: "1970-01-01"
relates_to:
  - "[[ADR-005]]"
  - "[[ADR-184]]"
supersedes: []
superseded_by: []
aliases: ["ADR 058"]
tags:
  - area/ops
  - status/proposto
  - type/adr
size_lines: 7
---

# ADR-058 — VPS CX32 para sizing

**Status:** Proposto (F7) • **Revisado:** 2026-05-09

> **Status atual (2026-05-09):** sugestão acoplada a [[ADR-005]] (também
> `Proposto`). Sizing CX32 vs CX22 é a recomendação atual mas continua
> aberta a revisão até a decisão de hosting ser fixada — ver [[ADR-184]]
> §"Decisão futura" para gatilho.

**Sugestão atual:** Hetzner CX32 (4 vCPU, 8GB, ~$8/mo). CX22 (4GB) é apertado com todos os containers + overhead de deploy.
