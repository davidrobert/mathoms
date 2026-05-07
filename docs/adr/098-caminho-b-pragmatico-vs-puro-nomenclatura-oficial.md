---
id: ADR-098
type: adr
title: "Caminho B pragmático vs puro: nomenclatura oficial"
status: Decidido
date: "2026-04-19"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 098"]
tags:
  - area/backend
  - area/persistence
  - area/pipeline
  - phase/a2
  - status/decidido
  - type/adr
size_lines: 44
---

# ADR-098 — Caminho B pragmático vs puro: nomenclatura oficial

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** Fase 8 pós-A5e · §17.2.5

**Contexto:** A proposta original de "Caminho B" (§3.2 do plano, linha 1190)
definia "script refatorado: recebe `StageConfig` + `ArtifactStore`, **sem I/O
de disco**". Isso implicava remover `_init_config`, eliminar globals de módulo
e fazer funções puras de `analyze_*`. Na prática, as sessões A2 (E3), A4b (E4),
A5d (E5), A5e (E5.N+E7) entregaram **duas variantes distintas** sem
formalizar a distinção.

**E3 (A2)** seguiu a proposta original: `E3ReconcilerAdapter` integra 8
domain services (`BankCanonicalizer`, `SaldoContinuityValidator`, etc.),
helpers extraídos, lazy init dos globais (A3b).

**E4/E5/E5.N/E7** optaram por reutilizar as funções `analyze_*` legadas
dentro de `main_with_store(ctx)`, preservando globals (`_init_config`,
`_TITULAR_KEY`, `FAMILY_CONFIG`, `_MEMBROS`, `_TITULAR_NOME`, `_CONJUGE_NOME`,
`GOALS_CONFIG`, `SCORING_CONFIG`, `FISCAL_CONFIG`, `METRICS`). Trade-off:
paridade 100% garantida em golden, mas testabilidade e thread-safety dos
scripts não mudaram. Os 14+ domain services extraídos em A1/A3c/A5a/A5b/A5c
ficam em prateleira — 1200+ testes cobrindo código que não é invocado por
`main_with_store`.

**Decisão:** Formalizar duas variantes no plano:

| Variante | Stages | Características |
|---|---|---|
| **Caminho B puro** | E3 (A2) | Refactor com domain services integrados, helpers extraídos, lazy init |
| **Caminho B pragmático** | E4, E5, E5.N, E7 | I/O via `ArtifactStore` ✅ · Wrapper limpo sem `stage_runner_compat` ✅ · **Mantém** `_init_config` + globals + `analyze_*` legadas · Domain services em prateleira |

O Caminho B pragmático **não é débito técnico definitivo** — ADR-100 fixa
A6d como commitment de converter os 5 stages pragmáticos para puros.

**Consequências:**
- ✅ Documentação honesta evita que próximo dev pense que services estão integrados.
- ✅ Nomenclatura comum para referência cross-team.
- ⚠️ Reconhece dívida técnica pendente nos 5 stages pragmáticos.
- ❌ Aceita que ~3500 linhas de domain services + testes ficam em prateleira
  até A6d executar.

**Artefatos:** [ARCHITECTURE.md §17.1](ARCHITECTURE.md#171-caminho-b-puro-vs-pragmático-estado-atual-e-alvo) (Caminho B puro vs pragmático); `CLAUDE.md` "Caminho B puro vs pragmático"; `docs/CHANGELOG.md` entry Sessão A5e.
