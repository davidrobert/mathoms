---
id: ADR-099
type: adr
title: "Reuse de `analyze_*` legadas em `main_with_store` (decisão de A5d/A5e)"
status: Decidido
date: "2026-04-19"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 099"]
tags:
  - type/adr
  - status/decidido
size_lines: 56
---

# ADR-099 — Reuse de `analyze_*` legadas em `main_with_store` (decisão de A5d/A5e)

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** Sessões A4b, A5d, A5e
**Contexto de ADR-098** (Caminho B pragmático)

**Contexto:** Em A5d (E5), A4b (E4), A5e (E5.N+E7), o escopo de cada sessão
era "fechar Caminho B para este stage". A abordagem purista — reescrever
`analyze_patrimonio`, `analyze_fluxo_caixa`, `calculate_score`,
`build_narrativas`, `run_cross_validation` usando os domain services já
extraídos — teria custo estimado de 5-8 sessões adicionais por stage,
inviabilizando a fase dentro do sprint.

A alternativa pragmática: `main_with_store(ctx)` lê E4 + baseline via
`ArtifactStore`, invoca as funções `analyze_*` legadas (preservando globals),
serializa output via helpers novos (`e5_serialization.build_e5_output`),
escreve via `store.write(...)`. Paridade 100% garantida no golden.

**Decisão:** Aceitar o padrão "`main_with_store` reutiliza `analyze_*`
legadas" como trade-off explícito. Ganhos imediatos:

1. **Bridge eliminado** — `pipeline/stages/e5.py`, `e4.py`, `e5n.py`, `e7.py`
   não importam mais `stage_runner_compat`.
2. **I/O abstraído** — `ArtifactStore.read/write` em todos os stages.
3. **Golden de paridade garantido** — bugs sutis em funções legadas
   permanecem reproduzíveis.
4. **Domain services preservados como foundation** — testados, sem cliente.
   Serão integrados em A6d (ver ADR-100).

**Princípios fixados:**
- **D6. `main_with_store` pode chamar funções legadas.** Não é violação da
  arquitetura; é estratégia de transição.
- **D7. Serialização via helpers novos** — output shape controlado por
  `e5_serialization.py`, não por dict inline em `main()`.
- **D8. Globais via `_init_config(ctx.root)`** — `main_with_store` reinicia
  globals do módulo antes de invocar legados; preserva thread-safety por
  processo Celery (fork-based).

**Consequências:**
- ✅ Fase 8 fechada em cronograma realista (3 sessões: A5a, A5b, A5c, A5d, A5e).
- ✅ Testes de paridade rigorosos (tolerância 0.01 BRL) garantem
  equivalência semântica ao legado.
- ⚠️ Globais continuam existindo — thread-unsafety por processo (Celery fork
  workers mitiga, mas `gunicorn --threads` ou `asyncio.run_in_executor` seriam
  problemáticos).
- ❌ Testes dos `analyze_*` continuam exigindo fixtures de disco
  (`life_plan_goals.md`, `tarefas.md`, `milhas.md`, `methodology.md`).
- ❌ 14+ domain services em prateleira até A6d.

**Artefatos:** `scripts/e4_categorize.main_with_store`,
`scripts/e5_analyze.main_with_store`, `scripts/e5n_narrativas.main_with_store`,
`scripts/e7_review.main_with_store`; goldens de paridade
`tests/test_e4_main_with_store_parity.py`,
`tests/test_e5_main_with_store_parity.py`,
`tests/test_e5n_e7_main_with_store_parity.py`.
