---
id: ADR-107
type: adr
title: "Remoção de `MaterializationBridge` e `stage_runner_compat` (A6c.1-2)"
status: Decidido
date: "2026-04-19"
relates_to: []
supersedes: ["[[ADR-086]]"]
superseded_by: []
aliases: ["ADR 107"]
tags:
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 35
---

# ADR-107 — Remoção de `MaterializationBridge` e `stage_runner_compat` (A6c.1-2)

**Status:** Decidido e executado (A6c.1-2) • **Data:** 2026-04-19 • **Commit:** `f7b824e`

**Contexto:** Após A5f (E1.5c em Caminho B pragmático) e A6a (LLM stages
escrevendo via `ArtifactStore`), o bridge ficou **sem clientes vivos** no
repo. Os 7 wrappers determinísticos (`pipeline/stages/e3.py`, `e4.py`,
`e5.py`, `e5n.py`, `e7.py`, `e15c.py` — e, via A6a, `e15.py` + `e2_llm.py`)
chamam `main_with_store(ctx)` direto. Nenhum código importa
`pipeline/stage_runner_compat.py` ou `pipeline/materialization_bridge.py`.
Manter código morto confunde auditorias futuras e contradiz docs.

**Decisão:**
1. **Deletar** `pipeline/materialization_bridge.py` e
   `pipeline/stage_runner_compat.py` no commit `f7b824e`.
2. **Manter** `main(root_dir)` legado nos 7 scripts determinísticos até
   A6c.3 — usado por CLI direto e golden tests de paridade.
3. **Testes estruturais** permanecem: imports não existem no codebase,
   falhariam imediatamente se recriados.

**Por que antes do A6-human:** remoção reversível por `git revert`, não
afetava produção (bridge não era invocado). Simplifica mensagem do
A6-human — falhas no cutover DB são reais, não resíduo de legado.

**Consequências:**
- ✅ Codebase livre de código morto.
- ✅ Arquitetura alvo pós-A6 mais próxima do estado real.
- ✅ A6c.3 (deletar `main(root_dir)` dos 6 scripts) concluído em
  2026-04-20 após A6-human; A6c.4 (docs) idem. **A6c completo**.
- ⚠️ R7 (princípio "MaterializationBridge temporário") fica apenas como
  registro histórico.

**Supersedes (parcialmente)**: ADR-086.
