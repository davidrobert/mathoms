---
id: ADR-001
type: adr
title: "SQLAlchemy 2.0 como ORM"
status: Decidido
phase: "F1"
date: "2026-04-13"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 001"]
tags:
  - area/persistence
  - status/decidido
  - type/adr
size_lines: 16
---

# ADR-001 — SQLAlchemy 2.0 como ORM

**Status:** Decidido (F1) • **Data:** 2026-04-13

**Contexto:** Precisamos de ORM async-compatible para FastAPI. Opções: SQLAlchemy 2.0, Tortoise ORM, SQL raw.

**Decisão:** SQLAlchemy 2.0 com async engine + Alembic para migrations.

**Consequências:**
- ✅ Maduro, grande ecossistema
- ✅ Async nativo (`AsyncSession`)
- ✅ Abstrai SQLite (dev) ↔ PostgreSQL (prod)
- ⚠️ Curva de aprendizado mais alta que Tortoise
- ⚠️ Precisa de `greenlet` + cuidados com `flush()` manual em async
