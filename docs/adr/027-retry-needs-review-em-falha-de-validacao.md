---
id: ADR-027
type: adr
title: "Retry → needs_review em falha de validação"
status: Decidido
phase: "F4"
date: "2026-04-15"
relates_to: ["[[ADR-270]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 027"]
tags:
  - area/llm
  - status/decidido
  - type/adr
size_lines: 17
---

# ADR-027 — Retry → needs_review em falha de validação

**Status:** Decidido (F4)

> **Emenda mecânica ([[ADR-270]], 2026-06-12):** falha de validação deixou de
> consumir o outer loop de retry — o reask fica no Instructor (`max_retries=2`)
> e o esgotamento vira `LLMValidationError` → `needs_review`. O contrato de
> produto desta ADR (nenhum dado perdido; user edita e faz resume) permanece;
> a contagem "3 retries" abaixo é histórica — mecânica vigente na ADR-270 §5-7.

**Decisão:** Se 3 retries falham validação, stage entra em `needs_review`. User edita JSON via API, depois faz resume do pipeline.

**Consequências:**
- ✅ Nenhum dado perdido
- ✅ User tem controle em edge cases
- ⚠️ Interface de review é complexa (JSON editor)
