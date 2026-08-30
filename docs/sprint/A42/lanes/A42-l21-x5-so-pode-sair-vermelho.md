---
id: A42.l21
type: lane
title: "O cross-check de proveniência da rodada unificada só pode sair vermelho, e agrega três causas distintas sob um rótulo"
sprint: A42
status: open
priority: P2
branch_slug: a42-l21-x5-so-pode-sair-vermelho
owner: senior-cto
depends_on: []
adrs: ["[[ADR-342]]", "[[ADR-416]]"]
tags: [type/lane, sprint/a42, status/open, priority/p2, area/dados]
---

# A42.l21 — `x5-so-pode-sair-vermelho`

> **Origem:** `PV12-04` da rodada unificada **U4** ([[PIPELINE-REVIEWS-active]] §r12).
> É a mesma patologia da [[A42.l18]] com o **sinal invertido**: lá o check não podia
> reprovar; aqui não pode aprovar.

## O defeito

O `X5` (`dev/_unified_xchecks/execucao.py`) marca como ofensor todo stage que loga
`completed` e não produz artefato com o `pipeline_run_id` do run, **quando o `StageSpec`
declara `writes`**. Três stages caem nisso **em todo run**, por três razões **diferentes**:

| stage | causa real |
|---|---|
| `extract_with_llm` | skip mal-carimbado (*"No unprocessed documents"*) |
| `generate_narratives` | **escreve** — sob outra `artifact_key`, por desenho de merge documentado no `CLAUDE.md` |
| `validate_cross` | read-only por construção |

Chamar os três de *"contrato falso"* apaga duas das três causas. E o conjunto é
**constante** em `U2`, `U3` e `U4` ⇒ **poder discriminante zero**: o check não pode ficar
verde, logo não pode informar nada.

## Critério de aceite

- [ ] O conjunto esperado é declarado por **igualdade de conjunto** (não isenção por
      arquivo), de modo que um **quarto** ofensor apareça como novidade.
- [ ] Cada uma das três causas é nomeada separadamente na saída.
- [ ] **Controle positivo:** introduzir um stage que declara `writes` e não escreve ⇒ o
      check reprova nomeando-o. Hoje ele já está vermelho e nada muda.

## Nota de escopo

O conserto é do **instrumento da rodada**, não do produto — mas mora aqui porque a tese da
sprint é falso-verde de instrumento, e um check que só dá vermelho é o mesmo defeito visto
do outro lado. Precedente: [[A42.l16]], cujo termo era `P ∨ ¬P` e também não discriminava.
