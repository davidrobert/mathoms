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

> **Nota de estado (audit r6, 2026-07-03):** o gate de CI **nunca foi
> implementado** — não há `fail_under`/`--cov-fail-under` em
> `.github/workflows/` nem em `pyproject.toml`; coverage é medida e
> publicada como artifact (`ci.yml`), não gated. O alvo abaixo segue
> aspiracional (o próprio `ci.yml` anota "F7C estende para: … coverage
> ≥85%").

**Contexto:** Buscar 100% line em 14K linhas de scripts legados é anti-pattern.

**Decisão:**
- Overall: ≥85% line, ≥75% branch
- Novo código: ≥95% line (CI gate)
- Crescimento orgânico a 90%+ ao longo do tempo
