---
id: A27.l1
type: lane
title: "Citação do parecer (E6→E5) como edge de lineage por chave natural"
sprint: A27
plan: PLAN-data-lineage
status: shipped
priority: P2
branch_slug: evidencia-lineage-edge
adrs:
  - "[[ADR-293]]"
  - "[[ADR-279]]"
depends_on:
  - "[[A26.l9]]"
parallel_with:
  - "[[A26.l9]]"
tags:
  - type/lane
  - sprint/a27
  - status/shipped
  - priority/p2
  - area/data-lineage
  - area/llm
---

# A27.l1 — `evidencia-lineage-edge` (Onda 6 · conclusão · Regime A)

> **Plano:** [[PLAN-data-lineage]] §Onda 6 (linha 365 · gate G6). Implementa
> [[ADR-293]] `Proposto`. Co-design `data-engineer` (contrato do edge) feito no F0 da
> ADR; revalidar `senior-cto` no slice 3 (estratégia de DELETE). **Dependência de
> contrato real com a [[A26.l9]]:** slices 1+3 paralelos à l9; slices 2+4 só após o
> merge da l9 (que cravam `ancoras[].path`). Não bloqueia o flip strict da A26.

## Problema

A citação verificada E5→E6 ([[ADR-279]] §E) vive **só** em
`_meta.evidencia_verification` do artifact do parecer — **desconectada** do grafo
`artifact_lineage_edge`. O reverse-lineage ([[A25.l3]]) e o drill-down de produto
([[A25.l5]]) não respondem "de onde veio este número no parecer?" — a camada mais
user-facing fica cega. Materializar como edge esbarra em dois fatos de contrato
(verificados em código, [[ADR-293]] §Contexto):

1. **Endereçamento posicional é instável.** `top_ativos` é ordenado por valor desc;
   `$.investimentos.top_ativos[3].valor` aponta para outro ativo após rebaseline.
   Persistir edge cross-run exige **chave estável**.
2. **O writer apaga tudo.** `lineage_edge_writer.materialize_lineage_edges` faz
   `DELETE ... WHERE workspace_id` (retenção N=1). Dois produtores na mesma tabela
   (E5→doc e E6→E5) se sobrescrevem.

## Decisão ([[ADR-293]])

Edge `edge_type = "parecer_citation"`: `dst` = identidade do item de parecer
(`risco[2]`, `sugestao_tatica[0]`) em `dst_field` string; `src` = folha E5 por **chave
natural** (`alocacao_por_classe` → `classe`; `top_ativos` → tupla `(membro, instituicao,
nome)` com `posicao` como tie-break). Chave confinada à **serialização do edge**
(`src_field` string) — **não** adiciona campo `id` ao payload E5 (isso rebaselinaria E5
+ exigiria ADR de contrato). Coexistência com retenção N=1 via **DELETE-por-produtor**
(`edge_type IN (...)`) ou materializador terminal único na mesma transação. **Zero
migration** esperado (cabe em `dst_field`/`edge_type` strings); coluna nova só se
necessário → aditiva online (`ADD COLUMN NULL`, sem backfill — tabela rebuildável N=1).

## Escopo (slices — ordem de dependência)

1. **Resolver chave natural** (∥ [[A26.l9]]) — helper que, dado um path de citação de
   lista, resolve a chave natural do item no E5 (`classe` / tupla `(membro, instituicao,
   nome)` + tie-break `posicao`). **Sem** tocar o schema E5.
2. **Emitir edge** (após o merge da l9) — no `parecer_orchestrator`, após
   `verify_evidencia`, materializar `edge_type="parecer_citation"`; reusar
   `lineage_edge_writer`. Consome `ancoras[].path` (contrato pós-l9).
3. **Coexistência com retenção N=1** (∥ [[A26.l9]]; revalidar `senior-cto`) — mudar o
   `materialize_lineage_edges` para delete-por-produtor **ou** materializador terminal
   único E5→doc + E6→E5 na mesma transação. Invariante: um produtor nunca apaga edges do
   outro.
4. **Reverse-lineage cobre parecer** (após o merge da l9) — estender a query reversa
   ([[A25.l3]]) + drill-down de produto ([[A25.l5]]) para responder "de onde veio este
   R$ do parecer?".

## Critério de aceite

- [[ADR-293]] `Proposto`→`Decidido (A27)` no merge da impl.
- **KR3 (= G6 do plano, verbatim):** edge `parecer_citation` reproduzível cross-run —
  teste com fixture sintética que reordena `top_ativos`: o edge por chave natural resolve
  o ativo certo; o por índice falharia. Reverse-lineage responde "de onde veio este R$ do
  parecer?".
- Teste de coexistência: E5→doc + E6→E5 sobrevivem ao DELETE N=1 (um produtor não apaga
  o outro).
- Zero migration (ou coluna aditiva online `ADD COLUMN NULL` se estritamente necessária);
  `make update-openapi-snapshot` se algum campo de edge for exposto.
- **Não recriar discovery** — a reordenação de `top_ativos` cross-run já foi resolvida
  analiticamente ([[ADR-293]] §Consequências, 2026-06-18).

## Owner

Agente da lane (A27); co-design `data-engineer` (contrato do edge, F0 da ADR-293) +
`senior-cto` (estratégia de DELETE no slice 3).

## Fechamento (2026-07-02)

- Slices 1+3 mergeados em [#715](https://github.com/davidrobert/mathoms/pull/715) /
  [#716](https://github.com/davidrobert/mathoms/pull/716) (resolver de chave natural +
  DELETE-por-produtor por `dst_stage` + writer `materialize_parecer_citation_edges`).
- Slices 2+4 neste PR: hook pós-run `_materialize_parecer_citation_edges` (só parecer
  publicado; âncora falhada nunca vira edge) + queries `parecer_citation_sources` e
  `parecer_items_depending_on_source_document` (2 hops coarse doc→parecer). KR3 provado
  por teste de reordenação de `top_ativos` (chave natural estável cross-run). Zero
  migration; sem endpoint novo (snapshot OpenAPI intacto). [[ADR-293]] flippada
  `Decidido (A27.l1)`.
