---
id: ADR-016
type: adr
title: "E0-route automático no upload"
status: Decidido
phase: "F2"
date: "1970-01-01"
relates_to: []
supersedes: []
superseded_by: ["[[ADR-079]]"]
aliases: ["ADR 016"]
tags:
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 14
---

# ADR-016 — E0-route automático no upload

**Status:** Decidido (F2)

> **Nota (2026-04-15):** parcialmente superseded por
> [ADR-079](#adr-079--content-first-classification-no-upload-web) — D79
> introduz classificação por **conteúdo** (não nome) no upload web; D16
> permanece válida para fluxo CLI legado.

**Decisão:** Ao uploadar, o documento é automaticamente classificado (banco, tipo, período) via regex do E0-route. Sem intervenção manual.

**Extensão (2026-04-15):** Documento também é copiado de `inbox/` para `data/{dest_group}/` imediatamente, para que o pipeline encontre os arquivos depois.
