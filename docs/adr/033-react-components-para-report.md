---
id: ADR-033
type: adr
title: "React components para report"
status: Decidido
phase: "F6"
date: "1970-01-01"
relates_to: []
supersedes: []
superseded_by: ["[[ADR-078]]"]
aliases: ["ADR 033"]
tags:
  - area/frontend
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 15
---

# ADR-033 — React components para report

**Status:** Decidido (F6)

**Contexto:** Como renderizar o relatório no frontend? iframe (reaproveita E6), sanitized HTML, React components.

**Decisão:** React components a partir do E5 JSON.

**Consequências:**
- ✅ Máximo controle (interatividade, dark mode, responsivo)
- ✅ Drill-down para Transaction Explorer
- ⚠️ Validação rigorosa necessária (L1 data accuracy, L2 section completeness) para evitar divergência com E6 HTML
- **Status da implementação:** Hybrid — iframe HTML + React chrome (toolbar, navegação)
