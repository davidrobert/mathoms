---
id: ADR-061
type: adr
title: "Telemetria privacy-first"
status: Decidido
phase: "F7"
date: "2026-04-15"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 061"]
tags:
  - type/adr
  - status/decidido
size_lines: 12
---

# ADR-061 — Telemetria privacy-first

**Status:** Decidido (F7)

> **Nota de estado (audit r6, 2026-07-03):** a tabela `UsageMetric` **nunca
> foi criada** (zero ocorrências em `backend/`). A metade "sem analytics
> externo" segue vigente.

**Decisão:** Tabela `UsageMetric` no DB próprio. Sem analytics externo (GA, Mixpanel, etc.).

**Consequências:**
- ✅ Zero third-party tracking
- ✅ Dados do user nunca saem do servidor
- ⚠️ Dashboards precisam ser construídos custom
