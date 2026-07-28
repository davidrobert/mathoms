---
id: ADR-035
type: adr
title: "`@media print` para PDF export"
status: Decidido
phase: "F6"
date: "2026-04-15"
relates_to: ["[[ADR-129]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 035"]
tags:
  - type/adr
  - status/decidido
size_lines: 17
---

# ADR-035 — `@media print` para PDF export

**Status:** Decidido (F6)

> **Nota r8 (2026-07-27):** o "upgrade path → Playwright" **foi tomado** — o export
> de PDF de produção é server-side via Playwright (`backend/app/services/pdf_renderer.py`)
> sobre a rota `/reports/[id]` ([[ADR-129]]: renderer HTML server-side descontinuado,
> React é o único renderer). Esta ADR permanece o registro da decisão inicial.

**Decisão:** PDF via `window.print()` + CSS `@media print`. Upgrade path → Playwright server-side se necessário.

**Consequências:**
- ✅ Zero custo, fiel ao browser
- ❌ Qualidade depende do browser do user
