---
id: A42.l21
type: lane
title: "O cross-check de proveniência da rodada unificada só pode sair vermelho, e agrega três causas distintas sob um rótulo"
sprint: A42
status: shipped
ship_pr: 1906
ship_date: "2026-08-31"
priority: P2
branch_slug: a42-l21-x5-so-pode-sair-vermelho
owner: senior-cto
depends_on: []
adrs: ["[[ADR-342]]", "[[ADR-416]]"]
tags: [type/lane, sprint/a42, status/shipped, priority/p2, area/dados]
---

# A42.l21 — `x5-so-pode-sair-vermelho`

> **Origem:** `PV12-04` da rodada unificada **U4** ([[PIPELINE-REVIEWS-active]] §r12).
> É a mesma patologia da [[A42.l18]] com o **sinal invertido**: lá o check não podia
> reprovar; aqui não pode aprovar. (A [[A42.l18]] shipou em #1870 — a patologia *dela*
> está fechada; a analogia descreve o achado da `U4`, não o estado atual daquele check.)

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

- [x] O conjunto esperado é declarado por **igualdade de conjunto** (não isenção por
      arquivo), de modo que um **quarto** ofensor apareça como novidade.
- [x] Cada uma das três causas é nomeada separadamente na saída.
- [x] **Controle positivo:** introduzir um stage que declara `writes` e não escreve ⇒ o
      check reprova nomeando-o. Hoje ele já está vermelho e nada muda.

## Nota de escopo

O conserto é do **instrumento da rodada**, não do produto — mas mora aqui porque a tese da
sprint é falso-verde de instrumento, e um check que só dá vermelho é o mesmo defeito visto
do outro lado. Precedente: [[A42.l16]], cujo termo era `P ∨ ¬P` e também não discriminava.

## Entregue — [#1906](https://github.com/davidrobert/mathoms/pull/1906)

> **2026-08-31.** O defeito procede. O conserto trocou o discriminador binário
> (`writes ≠ ∅`) por uma **escada de causas**, cada uma nomeada e cada uma
> falsificável isoladamente. Diff só em `dev/` e `tests/` — `stage_spec.py` fica
> intacto de propósito (o `PV10-10` rebaixou essa perna para P3 ao medir que
> `writes` é ornamental).

| classe | origem | como cai |
|---|---|---|
| `SEM-TRABALHO` | evidência do run | tirar o carimbo ⇒ `OFENSOR` |
| `SEM-WRITES-DECLARADOS` | `StageSpec.writes == ()` | — |
| `ESCREVE-EM-OUTRA-KEY` | **declarada** + cross-check na fonte | alvo muda, ou alvo sem artefato ⇒ `VENCIDA` |
| `READ-ONLY` | **declarada** + cross-check na fonte | ganha call-site de write ⇒ `VENCIDA` |
| `OFENSOR` | residual | — |

Varredura sobre o histórico completo de runs: **103 `FECHA` · 21 `DIVERGE` · 5
`INAPLICAVEL`**. Antes era `DIVERGE 3` constante. Os 21 são runs antigos com
stage `completed` sem artefato pinado no run — o que o `X5` existe para achar;
os 5 são runs sem nenhum stage `completed` (população vazia não é veredito).

### Duas correções do enunciado

1. **Eram 4 causas, não 3.** `unlock_documents`/`route_documents` já saíam isentos
   por `writes=∅`, sem rótulo próprio — a 4ª causa existia e estava muda.
2. **"Zero trabalho" tem duas grafias, e a lane só nomeou uma.** O enunciado
   chama `extract_with_llm` de *skip mal-carimbado*; a 1ª versão do conserto,
   fiel a ele, reprovava o stage em **5 dos 25** runs recentes do dogfood — ali
   ele não carimba `skipped`, sai por `{"success": true, "total_processed": 0}`.
   Os **mesmos** 4 stages usam as duas grafias conforme a saída que tomam
   (`skipped` em 8 stages, `total_processed` em 4). É a classe de falso-positivo
   que o `PV10-10` deu por **conhecida e não codificada**. As duas carregam a
   mesma informação — nenhuma diz se o stage *devia* ter tido trabalho — logo
   valem o mesmo veredito, e a divergência de grafia fica nomeada no detalhe.
   `total_processed: 0` **com erros** continua ofensor.

### Bateria de mutação — 8/8 vermelhas

A que sobreviveu na 1ª rodada virou teste próprio: `_ler_fonte` devolvendo `""`
em vez de `None`. A dispensa `READ-ONLY` afirma **ausência** de write, e `""` tem
zero writes — arquivo sumido satisfazia a declaração de graça. Afirmação de
ausência sobre fonte única, em forma de gate.
