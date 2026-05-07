---
id: ADR-002
type: adr
title: "Filesystem local para storage"
status: Decidido
phase: "F2"
date: "2026-04-13"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 002"]
tags:
  - type/adr
  - status/decidido
size_lines: 15
---

# ADR-002 — Filesystem local para storage

**Status:** Decidido (F2) • **Data:** 2026-04-13

**Contexto:** Onde armazenar documentos uploaded e outputs do pipeline?

**Decisão:** Filesystem local por tenant. S3/MinIO só na F7 se necessário.

**Consequências:**
- ✅ Simples. Backup via pg_dump + volume snapshot (F7)
- ✅ Zero dependências externas no MVP
- ❌ Não escala horizontalmente (um VPS)
- ❌ Backup é manual/cron
