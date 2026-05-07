---
id: ADR-026
type: adr
title: "Instructor + Pydantic para structured output"
status: Decidido
phase: "F4"
date: "1970-01-01"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 026"]
tags:
  - type/adr
  - status/decidido
size_lines: 12
---

# ADR-026 — Instructor + Pydantic para structured output

**Status:** Decidido (F4)

**Decisão:** Instructor enforça output Pydantic no LLM com auto-retry em validation failure.

**Consequências:**
- ✅ Menos código custom de parsing
- ✅ Retry automático com erros de validação no prompt
- ✅ Pydantic v2 nativo
