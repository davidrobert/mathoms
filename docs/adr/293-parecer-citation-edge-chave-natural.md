---
id: ADR-293
type: adr
title: "Citação de parecer (E6→E5) como edge de lineage por chave natural"
status: Decidido
phase: "A27 · Onda 6"
date: "2026-06-17"
relates_to:
  - "[[ADR-279]]"
  - "[[ADR-292]]"
supersedes: []
superseded_by: []
aliases: ["ADR 293", "parecer citation edge", "evidencia chave natural"]
tags:
  - type/adr
  - status/decidido
  - area/data-lineage
  - area/llm
  - phase/a27
---

# ADR-293 — Citação de parecer (E6→E5) como edge de lineage por chave natural

**Status:** Decidido (A27 · Onda 6) • **Data:** 2026-06-17 •
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
3. **Coexistência com retenção N=1:** o DELETE passa a ser **por produtor**. **Mecanismo
   decidido (co-design `senior-cto` 2026-07-01, refina esta ADR):** discriminar por
   **`dst_stage`** (`delete(...).where(dst_stage == <stage do produtor>)`), **não** por
   `edge_type` — o `edge_type` do E5→doc é set **aberto** (data-driven do `_lineage.fields[]`),
   enquanto `dst_stage` é 1:1 por produtor (E5→doc → `E5`; parecer_citation →
   `review_finances_holistic`), robusto a `edge_type` novo sem allow-list. Materializador
   terminal único (alternativa) rejeitado: só ganha atomicidade, inútil numa tabela
   rebuildável N=1, e força re-derivação em rerun parcial. **Invariante de órfão:** o writer
   do E6 só materializa se houver E5-com-`_lineage` no run corrente (espelha o guard do E5) —
   senão a citação apontaria para E5 de outro run. Invariante central: **um produtor nunca
   apaga edges do outro**.
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
- **Gate de discovery (pré-impl, A27) — RESOLVIDO 2026-06-18:** medir se
  `top_ativos` reordena entre runs. **Medição empírica em prod-local bloqueada:**
  os artefatos E5 em `pipeline_artifacts.content_json` são Fernet-encrypted
  (`{"_encrypted": true, ...}`) — não decripto dado financeiro real para medir
  ordenação. **Conclusão analítica (conclusiva, dispensa o empírico):**
  `top_ativos_analyzer` ordena por `valor` desc; a magnitude relativa dos ativos
  muda mês a mês (novo extrato, rebaseline) → a posição `[idx]` aponta para outro
  ativo entre runs. Logo a **chave natural é pré-requisito duro** do edge (não
  over-engineering). Salvaguarda na impl: teste de reprodutibilidade cross-run
  com fixture sintética (reordena a lista; o edge por chave natural ainda resolve
  o ativo certo; o por índice falharia).

## Escopo de implementação

A27 / [[PLAN-data-lineage]] §Onda 6. Lane única (chave natural + edge são **uma**
decisão: edge sem chave = lineage podre; chave sem edge = código morto). PR de
implementação flippa esta ADR → `Decidido (A27)`.

**Slices (ordem de dependência):**

1. **Resolver chave natural** — helper que, dado um path de citação de lista
   (`$.investimentos.top_ativos[i].valor`), resolve a chave natural do item no E5:
   `alocacao_por_classe` → `classe` (enum único); `top_ativos` → tupla
   `(membro, instituicao, nome)` com `posicao` como tie-break. **Sem** tocar o
   schema E5 (chave fica só na serialização do edge — zero migration).
2. **Emitir edge** — no `parecer_orchestrator`, após `verify_evidencia`, materializar
   `edge_type="parecer_citation"`: `src` = folha E5 por chave natural; `dst` =
   identidade do item de parecer (`risco[2]`, `sugestao_tatica[0]`) em `dst_field`
   string. Reusar `lineage_edge_writer`.
3. **Coexistência com retenção N=1** — o `materialize_lineage_edges` fazia
   `DELETE ... WHERE workspace_id` (apagava tudo). **Entregue (A27.l1 slice 3):**
   delete-por-produtor via **`dst_stage`** (E5→doc apaga `dst_stage == "E5"`;
   `materialize_parecer_citation_edges` apaga `dst_stage == "review_finances_holistic"`)
   + guard de órfão no writer do E6. Invariante: um produtor nunca apaga edges do outro.
4. **Reverse-lineage cobre parecer** — estender a query reversa ([[A25.l3]]) +
   drill-down de produto ([[A25.l5]]) para responder "de onde veio este R$ do
   parecer?".

**Gates:** zero migration (confinar a `dst_field`/`edge_type` strings; coluna nova
só se necessário → aditiva online `ADD COLUMN NULL`, tabela rebuildável N=1). Teste
de reprodutibilidade cross-run (reordena lista → edge por chave natural ainda
resolve certo). Teste de coexistência (E5→doc + E6→E5 sobrevivem ao DELETE).
Co-design `data-engineer` (contrato do edge) feito no F0 desta ADR; revalidar
`senior-cto` no slice 3 (estratégia de DELETE).
