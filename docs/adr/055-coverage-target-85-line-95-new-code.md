---
id: ADR-055
type: adr
title: "Coverage target: ≥85% line + ≥95% new code"
status: Decidido
phase: "F7"
date: "2026-04-15"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 055"]
tags:
  - type/adr
  - status/decidido
size_lines: 12
---

# ADR-055 — Coverage target: ≥85% line + ≥95% new code

**Status:** Decidido (F7)

**Contexto:** Buscar 100% line em 14K linhas de scripts legados é anti-pattern.

**Decisão:**
- Overall: ≥85% line, ≥75% branch
- Novo código: ≥95% line (CI gate)
- Crescimento orgânico a 90%+ ao longo do tempo
