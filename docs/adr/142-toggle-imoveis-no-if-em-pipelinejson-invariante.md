---
id: ADR-142
type: adr
title: "Toggle `imoveis_no_if` em `pipeline.json` + invariante anti-dupla-contagem"
status: Decidido
date: "2026-04-27"
relates_to: ["[[ADR-140]]", "[[ADR-143]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 142"]
tags:
  - type/adr
  - status/decidido
size_lines: 30
---

# ADR-142 — Toggle `imoveis_no_if` em `pipeline.json` + invariante anti-dupla-contagem

**Status:** Decidido • **Data:** 2026-04-27

**Contexto:** Em `ea22837` introduzimos no `definitions.md §FÓRMULAS PATRIMONIAIS` e em `FORMULAS.md` o conceito de **investível efetivo** = `investivel_financeiro + (cat_2 if workspace.imoveis_no_if else 0)`. Em paralelo, `goal.if.v2.schema.json` introduziu `renda_passiva_atual_mensal_brl` que desconta no denominador. Auditoria rodada 2 (item R7 / financial-planner 1.4) identificou **risco de dupla contagem**: se `imoveis_no_if=true` e `renda_passiva_atual` inclui aluguéis líquidos, os imóveis aparecem **duas vezes** — somam no numerador (cat_2 em investível efetivo) e descontam no denominador (renda passiva atual reduz `if_meta_liquida`).

**Decisão:** Adotar **invariante de exclusão mútua** entre os dois caminhos:

- Se `pipeline.json:patrimonio_composicao.imoveis_no_if = true`:
  - cat_2 entra em `investivel_efetivo`
  - `goal.if.inputs.renda_passiva_atual_mensal_brl` **deve excluir aluguéis líquidos** (pode incluir dividendos + juros — mas não a renda gerada por imóveis já contados como capital).
- Se `imoveis_no_if = false`:
  - cat_2 fora de `investivel_efetivo`
  - `renda_passiva_atual_mensal_brl` **deve incluir aluguéis líquidos** (são a renda passiva real e não há contagem dupla).

**Default:** `imoveis_no_if = true` para o workspace dogfood inicial (yield líquido ~6% > TRS 5%) — já gravado em `pipeline.json` em `ea22837`. Para workspaces onde yield líquido < TRS (vacancia, ou imóveis com retorno baixo), recomenda-se override `false`.

**Por que validar a invariante mas não automatizar:** o produto não calcula yield líquido por imóvel (depende de carnê-leão real, vacância histórica, despesas de manutenção). A escolha do toggle é decisão consultiva do planejador. Hoje vive em `pipeline.json` global; um futuro override por workspace exigiria coluna `Workspace.imoveis_no_if` (lane separada).

**Validação:** documentada em `definitions.md §FÓRMULAS PATRIMONIAIS:Validações`. `e5_analyze.py` deve emitir warning quando `imoveis_no_if=true` e `renda_passiva_atual_mensal_brl > sum(aluguéis_categorizados_como_renda_recorrente)` — sinaliza provável dupla contagem.

**Consequências:**

- `progresso_if` continua `investivel_efetivo / if_meta_liquida × 100` (FORMULAS.md), mas com invariante respeitada o resultado é correto.
- Famílias podem comparar dois cenários (toggle on/off) para entender impacto — útil pedagogicamente.
- "Por workspace" do toggle é hoje **promessa de doc**, não realidade — fica catalogado como débito.

**Relaciona-se a:** [ADR-140](#adr-140--goal-if-schema-v2-renda-passiva-atual--if-meta-líquida) (motivação direta — `renda_passiva_atual_mensal_brl`), [FORMULAS.md §Patrimônio](FORMULAS.md). Documentação histórica de fórmulas patrimoniais foi dissolvida em [ADR-143](#adr-143--docsmethodology-é-rules-as-code-sprint-a76) (A7.6) — invariantes hoje vivem como docstrings em `pipeline/domain/services/` (composição) e em `docs/ARCHITECTURE.md §Glossário` (definitions).
