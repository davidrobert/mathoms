---
id: ADR-027
type: adr
title: "Retry → needs_review em falha de validação"
status: Decidido
phase: "F4"
date: "1970-01-01"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 027"]
tags:
  - area/llm
  - status/decidido
  - type/adr
size_lines: 12
---

# ADR-027 — Retry → needs_review em falha de validação

**Status:** Decidido (F4)

**Decisão:** Se 3 retries falham validação, stage entra em `needs_review`. User edita JSON via API, depois faz resume do pipeline.

**Consequências:**
- ✅ Nenhum dado perdido
- ✅ User tem controle em edge cases
- ⚠️ Interface de review é complexa (JSON editor)
