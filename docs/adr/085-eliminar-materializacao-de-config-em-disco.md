---
id: ADR-085
type: adr
title: "Eliminar materialização de config em disco"
status: Decidido
phase: "parcial — implementação na Fase 4"
date: "2026-04-19"
relates_to: []
supersedes: ["[[ADR-020]]"]
superseded_by: []
aliases: ["ADR 085"]
tags:
  - type/adr
  - status/decidido
size_lines: 32
---

# ADR-085 — Eliminar materialização de config em disco

**Status:** Decidido (parcial — implementação na Fase 4) • **Data:** 2026-04-19
**Supersedes:** ADR-020

**Contexto:** ADR-020 materializava 5 configs editáveis em
`storage/<ws>/config/` a cada run para que scripts do pipeline lessem do
disco. Efeitos colaterais:

- Drift entre DB ↔ disco exige script de validação (`validate_adapter_parity.py`).
- I/O desnecessário a cada run.
- Acoplamento entre `config/` no disco e `PipelineConfig`/`FamilyMember`/…
  no DB.

Com `StageConfig` (ADR-088) passando config por parâmetro, a materialização
torna-se redundante.

**Decisão:** `StageConfig.from_context(ctx)` lê diretamente de
`ctx.config_overrides` (dict do DB, injetado em `for_tenant`) ou do disco
legado (CLI dev). `config_materializer.py` é no-op a partir da Fase 4 e removido
quando nenhum script legado depender mais dele.

`validate_adapter_parity.py` é reposto como validação DB ↔ `StageConfig`
(plano §12).

**Consequências:**
- ✅ Uma única fonte de verdade (DB em web, `config/` em CLI).
- ✅ Remove race condition entre materialização e execução.
- ⚠️ CLI dev continua lendo `config/<name>.json` — comportamento preservado.
- ❌ Scripts legados (Caminho A) ainda leem do disco — mitigado pelo bridge.
