---
id: ADR-020
type: adr
title: "Materializar config em disco"
status: Decidido
phase: "F3"
date: "1970-01-01"
relates_to: []
supersedes: []
superseded_by: ["[[ADR-085]]"]
aliases: ["ADR 020"]
tags:
  - type/adr
  - status/decidido
size_lines: 19
---

# ADR-020 — Materializar config em disco

**Status:** Decidido (F3)

> **Nota (Sprint A6):** superseded por
> [ADR-085](#adr-085--eliminar-materialização-de-config-em-disco) —
> material config em disco eliminada em favor de `ConfigStore` ([ADR-134](#adr-134--configstore-protocolo-de-leitura-tipado-pipeline--backend))
> e cutover concluído em A7.1.

**Contexto:** Scripts usam `_init_config(base_dir)` que lê de `base_dir/config/`. Como injetar config do DB sem reescrever 12+ scripts?

**Decisão:** `materialize_config()` copia `config/` global para `tenant/config/`, depois sobrescreve apenas os configs editados no DB.

**Consequências:**
- ✅ Zero mudança nos scripts legados
- ✅ Fallback automático (configs não editados lêem do global)
- ⚠️ ~500KB de I/O por run (negligível)
