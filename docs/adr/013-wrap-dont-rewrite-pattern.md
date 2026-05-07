---
id: ADR-013
type: adr
title: "\"Wrap, Don't Rewrite\" pattern"
status: Decidido
phase: "F0"
date: "2026-04-12"
relates_to: []
supersedes: []
superseded_by: ["[[ADR-072]]"]
aliases: ["ADR 013"]
tags:
  - area/multitenancy
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 24
---

# ADR-013 — "Wrap, Don't Rewrite" pattern

**Status:** Decidido (F0) • **Data:** 2026-04-12

> **Nota (2026-04-15):** parcialmente superseded por
> [ADR-072](#adr-072--multi-tenancy-workspace_id-scoping-explícito--workspacemember-para-multi-família) — F8 formaliza
> migração eventual dos wraps em adapters DB (configs de usuário saem do
> repo). O padrão "wrap" continua válido para scripts que não migram (E0
> route, E2 parsers).

**Contexto:** Scripts legados (E5=107KB, E6=197KB) têm lógica refinada de domínio. Reescrever é arriscado e demorado.

**Decisão:** Cada script ganha `_init_config(base_dir)` + `main(root_dir=None)`. Wrappers finos em `pipeline/stages/` (3-15 linhas).

**Consequências:**
- ✅ CLI continua funcionando idêntico
- ✅ Thread-safe (cada call re-inicializa seus globals)
- ✅ Multi-tenant via `root_dir` injection
- ✅ Testável com `main(root_dir=tmp_dir)`
- ⚠️ Globals patteren persiste (código legado não idiomático)

Alternativa descartada: injetar config via dict. Exigiria refatorar `_init_config` em todos os scripts.
