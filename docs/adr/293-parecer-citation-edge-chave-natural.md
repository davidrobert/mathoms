---
id: ADR-293
type: adr
title: "Citação de parecer (E6→E5) como edge de lineage por chave natural"
status: Proposto
phase: "A26 · Onda 6 (impl. A27)"
date: "2026-06-17"
relates_to:
  - "[[ADR-279]]"
  - "[[ADR-292]]"
supersedes: []
superseded_by: []
aliases: ["ADR 293", "parecer citation edge", "evidencia chave natural"]
tags:
  - type/adr
  - status/proposto
  - area/data-lineage
  - area/llm
  - phase/a26
---

# ADR-293 — Citação de parecer (E6→E5) como edge de lineage por chave natural

**Status:** Proposto (A26 · Onda 6; implementação A27) • **Data:** 2026-06-17 •
**Relaciona** [[ADR-279]] (lineage field-level + índice reverso), [[ADR-292]]
(coerção de `evidencia_path`).

> **Não reabre [[ADR-279]] no contrato de citação** ([[A26.l7]] cobre listas
> conformando o v1). Reabre **só** o item que a §E deferiu explicitamente —
> "índice reverso por `rule_ref` deferido até F7": esta ADR materializa a
> citação do parecer no grafo de lineage, antes de F7, com escopo restrito.

## Contexto

A citação verificada E5→E6 ([[ADR-279]] §E) hoje vive **só** em
`_meta.evidencia_verification` do artifact do parecer — **desconectada** do grafo
`artifact_lineage_edge`. Consequência: o reverse-lineage ([[A25.l3]]) e o
drill-down de produto ([[A25.l5]]) não respondem "de onde veio este número no
parecer?" — exatamente a camada mais user-facing fica cega.

Materializar a citação como edge esbarra em dois fatos de contrato (co-design
`data-engineer` 2026-06-17, verificado em código):

1. **Endereçamento posicional é instável.** `top_ativos` é ordenado por valor desc
   ([`top_ativos_analyzer.py`](../../pipeline/domain/services/top_ativos_analyzer.py)).
   Uma edge `$.investimentos.top_ativos[3].valor` materializada no run R aponta
   para **outro ativo** após o run R+1 se a ordem mudar. Posicional é seguro só
   *dentro do run* (citação inline); **persistir edge cross-run exige chave estável**.
2. **O writer apaga tudo.** [`lineage_edge_writer.materialize_lineage_edges`](../../backend/app/services/lineage_edge_writer.py)
   faz `delete(ArtifactLineageEdge).where(workspace_id==...)` (retenção N=1). Dois
   produtores na mesma tabela (E5→doc e E6→E5) **se sobrescrevem**.

## Decisão (proposta)

1. **Edge de citação:** `edge_type = "parecer_citation"`; `dst` = identidade do item
   de parecer (`risco[2]`, `sugestao_tatica[0]`) em `dst_field` string; `src` = folha
   E5 por **chave natural**, não índice.
2. **Chave natural, sem mudar o E5:** `alocacao_por_classe` → `classe` (enum único);
   `top_ativos` → tupla `(membro, instituicao, nome)` com `posicao` como tie-break
   determinístico. Confinada à **serialização do edge** (`src_field` string) — **não**
   adiciona campo `id` ao payload E5 (isso rebaselinaria E5 + exigiria ADR de contrato).
3. **Coexistência com retenção N=1:** o DELETE passa a ser **por produtor**
   (`delete(...).where(edge_type.in_(<próprias do produtor>))`) **ou** um
   materializador terminal único grava E5→doc + E6→E5 na mesma transação. Decisão
   final do mecanismo fica no PR de implementação; o invariante é: **um produtor
   nunca apaga edges do outro**.
4. **Zero migration** se a identidade do item de parecer couber em `dst_field`/
   `edge_type` (strings existentes). Coluna nova (`producer`/`claim_id`) só se
   necessário → aditiva online (`ADD COLUMN NULL`, sem backfill — tabela é
   rebuildável N=1, regenera no próximo run).

## Alternativas rejeitadas

- **Índice posicional** — lineage podre cross-run (fato 1).
- **Campo `id` canônico no E5** — rebaselina E5, ADR de contrato de payload, custo
  desproporcional vs. chave natural já presente.
- **`[*]` agrupado no `dst`/`src`** — resolve para lista inteira; `_numeric_leaves`
  + `any()` maximiza falso-verde ([[A26.l7]] usa `[idx].subkey` escalar por isso).

## Consequências

- Reverse-lineage e drill-down passam a cobrir as afirmações do parecer.
- Custo: +1 produtor de edge; risco mitigado pela regra de DELETE-por-produtor.
- **Gate de discovery (pré-impl, A27):** medir empiricamente se `top_ativos`
  reordena entre runs reais. Se a ordem for estável na prática, a chave natural
  vira defesa barata; se reordenar (esperado), é pré-requisito duro do edge.

## Escopo de implementação

A27 / [[PLAN-data-lineage]] §Onda 6. Lane única (chave natural + edge são **uma**
decisão: edge sem chave = lineage podre; chave sem edge = código morto). PR de
implementação flippa esta ADR → `Decidido (A27)`.
