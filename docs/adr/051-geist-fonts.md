---
id: ADR-051
type: adr
title: "Geist fonts"
status: Decidido
phase: "F4.5"
date: "2026-04-15"
relates_to: []
supersedes: []
superseded_by: ["[[ADR-076]]"]
aliases: ["ADR 051"]
tags:
  - area/frontend
  - status/decidido
  - type/adr
size_lines: 7
---

# ADR-051 — Geist fonts

**Status:** Decidido (F4.5)

> **Superseded por [[ADR-076]]** (banner adicionado no audit r6,
> 2026-07-03): o corpo da ADR-076 registra "Geist substituída por Plus
> Jakarta Sans (display) + Inter (body)" e `frontend/src/app/layout.tsx`
> importa Inter + Plus Jakarta Sans + JetBrains Mono — zero Geist. A
> decisão de fonte foi integralmente revertida (supersedure **total**; o
> rótulo "parcial" na 076 só se aplica ao par ADR-050). Sobrevive apenas o
> princípio "mono para números financeiros (tabular-nums)", hoje via
> JetBrains Mono.

**Decisão:** Geist Sans + Geist Mono via `next/font/google`. Mono para números financeiros (tabular-nums).
