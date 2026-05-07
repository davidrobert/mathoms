---
id: ADR-053
type: adr
title: "`Intl` nativo para datas"
status: Decidido
phase: "F4.5"
date: "1970-01-01"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 053"]
tags:
  - area/frontend
  - status/decidido
  - type/adr
size_lines: 9
---

# ADR-053 — `Intl` nativo para datas

**Status:** Decidido (F4.5)

**Decisão:** `Intl.DateTimeFormat` / `Intl.NumberFormat` nativos. date-fns adiado para F6 (DateRangePicker).

**Rationale:** Locale-aware, zero deps externas.
