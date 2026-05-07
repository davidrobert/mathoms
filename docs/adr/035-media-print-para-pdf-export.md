---
id: ADR-035
type: adr
title: "`@media print` para PDF export"
status: Decidido
phase: "F6"
date: "1970-01-01"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 035"]
tags:
  - type/adr
  - status/decidido
size_lines: 11
---

# ADR-035 — `@media print` para PDF export

**Status:** Decidido (F6)

**Decisão:** PDF via `window.print()` + CSS `@media print`. Upgrade path → Playwright server-side se necessário.

**Consequências:**
- ✅ Zero custo, fiel ao browser
- ❌ Qualidade depende do browser do user
