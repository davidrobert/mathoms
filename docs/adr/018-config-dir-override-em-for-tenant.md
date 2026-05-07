---
id: ADR-018
type: adr
title: "`config_dir` override em `for_tenant()`"
status: Decidido
phase: "F2"
date: "1970-01-01"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 018"]
tags:
  - type/adr
  - status/decidido
size_lines: 7
---

# ADR-018 — `config_dir` override em `for_tenant()`

**Status:** Decidido (F2)

**Decisão:** `WorkspaceContext.for_tenant()` aceita `config_dir` apontando para `config/` global ou para tenant-specific. Na F3, passa a apontar para tenant config materializada.
