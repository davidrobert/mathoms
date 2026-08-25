---
id: ADR-411
type: adr
title: "O diagnóstico sai do artefato em todo desfecho, e a posição da razão é parte da identidade da row"
status: Proposto
phase: A40.l81/RV8-09
date: "2026-08-24"
relates_to:
  - "[[ADR-272]]"
  - "[[ADR-308]]"
  - "[[ADR-343]]"
  - "[[ADR-356]]"
  - "[[ADR-357]]"
  - "[[ADR-371]]"
  - "[[ADR-404]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 411"
  - "sink de diagnóstico em todo desfecho"
  - "RV8-09"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/observability
---

# ADR-411 — O diagnóstico sai do artefato em todo desfecho

**Status:** Proposto (A40.l81 · RV8-09) • **Data:** 2026-08-24 • **Relaciona**
[[ADR-272]] (a razão tipada e a tabela consultável), [[ADR-404]] (a superfície de
diagnóstico nunca aborta a execução que documenta — **restrição**, não objeto
desta nota), [[ADR-357]] (WARN-first: o stage entrega e a degradação é derivada),
[[ADR-343]] (o snapshot PII-safe que passa a ler a tabela).

> **Esta nota não reabre a ADR-404.** A ordem *controle primeiro e sozinho,
> analítico depois em sessão própria e fail-open* continua valendo, intacta.
> Aqui se decide **em quantos desfechos** o analítico roda, **onde** a razão é
> procurada dentro do artefato, e **o que identifica** uma row. Teste de
> falseamento aplicado na escrita: se a §Decisão coubesse em *"chamar o sink
> também no ramo de sucesso"*, isto seria emenda à 404 e não nota nova — não
> cabe, porque D2 e D3 mudam a colheita e a chave.

## Contexto — medido, não herdado

Run `d0f6260a` (2026-08-24), remedido nesta lane com `dev/dump_artifact.py` sobre
o artefato guardado, não sobre a prosa da revisão:

| onde, no artefato do `consolidate_baseline` | code | Σ `occurrence_count` |
|---|---|---|
| `validation.review_reasons` | `domain.baseline_divergence` | 2 |
| `imoveis_consolidados[].review_reasons` | `domain.property_identity_uncanonical` | 2 |

`validation` **não carrega a chave `valid`** — logo `_has_validation_errors` é
falso, o stage entrega, e o run inteiro fecha `completed`. A tabela
`review_reasons` do mesmo run tem 2 rows, **ambas de `analyze_finances`** — o
único stage que pausou. Cobertura do stage WARN-first: **0 de 4**.

A causa não é o `_drop_unknown_codes`: os dois códigos estão na allowlist. É que
`record_review_reasons` tem call-site único dentro de `_record_stage_needs_review`,
que só roda no desfecho `needs_review`.

## Decisão

**D1 — o sink roda no caminho de saída, não num ramo.** Todo desfecho de stage
que produz `detail` — entregue, degradado, falho ou pausado — materializa a razão.
O ramo de pausa deixa de ser o portão do analítico. Desfecho por exceção
(`result is None`) não tem `detail` e colhe zero por construção, não por omissão.

**D2 — a colheita caminha o artefato inteiro, e o caminhamento é um só.** A razão
é procurada em **qualquer** posição (`validation.review_reasons` e as coleções
aninhadas como `imoveis_consolidados[].review_reasons`), não no caminho de topo.
A alternativa — promover a razão de item no produtor — foi **rejeitada**: fecharia
o `property_identity_enricher` e deixaria a classe aberta para o próximo produtor
que aninhar. O gate usa **a mesma função** de caminhamento que o sink; um
predicado que caminhasse por conta própria certificaria o meio-fix, que é o
defeito que [[A40.l59]] e [[A40.l25]] já registraram.

**D3 — a posição entra na identidade da row.** A chave de consolidação passa de
`(run, code)` para `(run, code, locator)`, onde `locator` é o caminho da coleção
que continha a razão. Sem isso o operador recebe ponteiro que não reencontra — o
defeito de RV8-19. O `locator` é **preenchível por construção** (quem colhe sabe
o caminho), nunca nasce impreenchível pelo produtor. Cardinalidade: o locator é
caminho de **coleção**, não de item — não multiplica row por imóvel.

**D4 — `StageReview` continua significando uma coisa só.** Aviso de run que
**completou** NÃO vira `StageReview`. `resume_run` só libera a retomada com zero
reviews `pending`, e publicar aviso ali passaria a pedir aprovação para um run
que não parou. A superfície do usuário para aviso-sem-pausa fica **deferida** com
dono e data (§Deferimento), na forma da [[ADR-356]] — não implícita.

**D5 — a tabela ganha leitor no mesmo ato.** `review_snapshot` passa a projetar
`(stage, locator, code) → Σ occurrence_count` e `compare_reviews` ganha perna que
alerta quando a razão cresce run-a-run. Escrita sem leitor declarada "entregue" é
falso-verde — a classe que o §r8 registrou em RV8-17 e RV8-12.

**D6 — a ordem da [[ADR-404]] é preservada em cada desfecho.** O controle commita
primeiro e sozinho; o sink vem depois, em sessão própria, fail-open. O sink é
chamado **de dentro do recorder terminal** de cada desfecho, depois do commit de
controle — nunca antes, senão grava diagnóstico de transição que pode não ter
acontecido.

## Correção de um número do critério da lane

O critério de aceite da [[A40.l81]] diz *"4 razões no artefato ⇒ 4 rows"*. Sob a
consolidação da [[ADR-272]] Fase 2 isso é **2 rows** (uma por `code`, agora por
`(code, locator)`) com `occurrence_count` 2 cada. O predicado honesto — e o que o
gate mede — é **Σ `occurrence_count` por `(code, locator)`**, não contagem de
rows. Um gate escrito como `count(rows) == 4` reprovaria o comportamento correto.

## Consequências

- Volume: rows por run deixam de ser função da pausa. O cap
  `_REVIEW_REASON_ROW_CAP` segue defensivo; o locator é de coleção e a
  cardinalidade real fica na ordem de dezenas.
- Retenção: `review_reasons.pipeline_run_id` é FK `ON DELETE CASCADE`
  ([[ADR-371]]) — row de diagnóstico morre com o run que a gerou. Nada a fazer.
- Rows históricas ficam com `locator` **vazio**, não nulo: a chave de
  consolidação compara por igualdade, e `NULL = NULL` é falso em SQL — locator
  nulo quebraria a idempotência que torna o redelivery do Celery seguro. `""`
  significa "não colhido"; o leitor o mostra como caminho desconhecido.

## Deferimento — superfície de usuário para aviso-sem-pausa (D4)

**Dono:** owner • **Condição de retomada:** quando houver decisão de produto sobre
como o relatório mostra aviso de run entregue. Até lá o aviso vive na tabela e no
snapshot, lido por operador, e `StageReview` segue exclusivo da pausa.
