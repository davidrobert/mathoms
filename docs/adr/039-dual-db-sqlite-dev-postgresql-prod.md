---
id: ADR-039
type: adr
title: "Dual DB: SQLite (dev) + PostgreSQL (prod)"
status: Decidido
phase: "F7"
date: "1970-01-01"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 039"]
tags:
  - type/adr
  - status/decidido
size_lines: 9
---

# ADR-039 — Dual DB: SQLite (dev) + PostgreSQL (prod)

**Status:** Decidido (F7)

**Decisão:** SQLite em dev (zero setup). PostgreSQL em prod. CI testa em PostgreSQL (mesmo DB que prod).

**Rationale:** Dual-test CI (SQLite + PG) dobra tempo de CI sem valor proporcional. SQLAlchemy abstrai ambos.
