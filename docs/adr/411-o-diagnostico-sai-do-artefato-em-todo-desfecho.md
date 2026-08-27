---
id: ADR-411
type: adr
title: "O diagnóstico sai do artefato em todo desfecho, e a posição da razão é parte da identidade da row"
status: Decidido
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
amended_at: ["2026-08-27"]
supersedes: []
superseded_by: []
aliases:
  - "ADR 411"
  - "sink de diagnóstico em todo desfecho"
  - "RV8-09"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/observability
---


> **Correção datada 2026-08-27 ([[A40.l84]] · closeout do #1771):** a premissa do D4
> estava escrita na forma **por camada** (*"`resume_run` só libera…"*) que a
> [[ADR-404]] §Emenda refutou. O **argumento** do D4 não muda; a premissa passa a
> dizer "toda entrada". Era o quinto sítio da mesma afirmação, e o único que o
> #1771 deixou passar.

# ADR-411 — O diagnóstico sai do artefato em todo desfecho

**Status:** Decidido (A40.l81 · RV8-09 · #1697) • **Data:** 2026-08-24 • **Relaciona**
[[ADR-272]] (a razão tipada e a tabela consultável), [[ADR-404]] (a superfície de
diagnóstico nunca aborta a execução que documenta — **restrição**, não objeto
desta nota), [[ADR-357]] (WARN-first: o stage entrega e a degradação é derivada),
[[ADR-343]] (o snapshot PII-safe que passa a ler a tabela).

> **Esta nota não reabre a ADR-404.** A ordem *controle primeiro e sozinho,
> analítico depois em sessão própria e fail-open* continua intacta. Aqui se
> decide **em quantos desfechos** o analítico roda, **em que canal** a razão é
> procurada, e **o que identifica** uma row.

## Contexto — medido, não herdado

Run `d0f6260a` (2026-08-24), remedido nesta lane com `dev/dump_artifact.py` sobre
o artefato guardado, não sobre a prosa da revisão:

| onde, no artefato do `consolidate_baseline` | code | Σ `occurrence_count` |
|---|---|---|
| `validation.review_reasons` | `domain.baseline_divergence` | 2 |
| `imoveis_consolidados[].review_reasons` | `domain.property_identity_uncanonical` | 2 |

A tabela `review_reasons` do mesmo run tem 2 rows, **ambas de
`analyze_finances`** — o único stage que pausou.

A causa não é o `_drop_unknown_codes`: os dois códigos estão na allowlist. São
**duas** causas, e a segunda só apareceu ao medir os `detail` do run inteiro:

**(i) o sink só roda no ramo de pausa.** `record_review_reasons` tem call-site
único dentro de `_record_stage_needs_review`. Medido em todos os stages do run:

| stage | desfecho | Σ occ no `detail` | persistido |
|---|---|---:|---:|
| `extract_baseline` | entregou | 11 | 0 |
| `reconcile_transactions` | entregou | 28 | 0 |
| `analyze_finances` | **pausou** | 3 | 3 |
| `consolidate_baseline` | entregou | 0 (no artefato: 4) | 0 |

**46 ocorrências emitidas, 3 persistidas — 6,5% de cobertura.** A lane
dimensionou o caso pelas 4 do `consolidate_baseline`; o volume dominante são as
39 de `reconcile_transactions` + `extract_baseline`, que já estavam no canal
certo e só esperavam o sink sair do ramo de pausa.

**(ii) o `consolidate_baseline` não escreve no canal que o sink lê.** O `detail`
dele **não tem bloco `validation` nenhum** — as 4 razões existem só dentro do
artefato. Mover a chamada do sink, sozinho, colheria **zero** para este stage.
Este é o achado que a lane não tinha, e sem ele o fix ficaria verde sobre o caso
que lhe deu origem.

## Decisão

**D1 — o sink roda no caminho de saída, não num ramo.** Todo desfecho que produz
`detail` — entregue, degradado, falho ou pausado — materializa a razão. Desfecho
por exceção (`result is None`) colhe zero por construção, não por omissão.

**D2 — a colheita caminha o payload inteiro, e o caminhamento é um só.** A razão
é procurada em **qualquer** posição (`validation.review_reasons` e as coleções
aninhadas como `imoveis_consolidados[].review_reasons`), nunca só no caminho de
topo. O gate usa **a mesma função** que o sink; um predicado que caminhasse por
conta própria certificaria o meio-fix, que é o defeito que [[A40.l59]] e
[[A40.l25]] já registraram. Mora em `pipeline/domain/` porque o produtor também a
usa (D2b) e `pipeline/**` não importa `backend/`.

**D2b — o `detail` é o canal, e o produtor declara nele o que o payload carrega.**
O sink lê o `detail` do stage, não o artefato. Ler o artefato de volta foi
**rejeitado**: as duas formas coexistiriam sem chave de dedup honesta — as 2
razões de imóvel do run medido têm conteúdo **idêntico** (mesmo `code`, mesmo
`offending_value`), então dedup por conteúdo colapsaria 2 em 1 e perderia uma
ocorrência real. Logo o produtor que só materializa razão dentro do artefato
passa a declará-la no `detail`, **colhida com a função de D2** — nunca montada à
mão a partir do caminho de topo, que deixaria 2 de 4 para trás. Sem `valid`: quem
decide pausa é o orquestrador ([[ADR-357]] §2).

**D3 — a posição entra na identidade da row.** A chave de consolidação passa de
`(run, code)` para `(run, code, locator)`, onde `locator` é o caminho da coleção
que continha a razão. Sem isso o operador recebe ponteiro que não reencontra — o
defeito de RV8-19. O `locator` é **preenchível por construção** (quem colhe sabe
o caminho), nunca nasce impreenchível pelo produtor. Cardinalidade: o locator é
caminho de **coleção**, não de item — não multiplica row por imóvel.

**D4 — `StageReview` continua significando uma coisa só.** Aviso de run que
**completou** NÃO vira `StageReview`. A retomada só é liberada com zero reviews sem
decisão — em **toda entrada**, não só pela rota HTTP ([[ADR-404]] D2 §Emenda
2026-08-27) —, e publicar aviso ali passaria a pedir aprovação para um run
que não parou. A superfície do usuário para aviso-sem-pausa fica **deferida** com
dono e data (§Deferimento 1), na forma da [[ADR-356]] — não implícita.

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

O critério da [[A40.l81]] diz *"4 razões no artefato ⇒ 4 rows"*. Sob a
consolidação da [[ADR-272]] Fase 2 isso é **2 rows** (uma por `(code, locator)`)
com `occurrence_count` 2 cada. O predicado honesto — e o que o gate mede — é
**Σ `occurrence_count`**, não contagem de rows: `count(rows) == 4` reprovaria o
comportamento correto.

## Consequências

- Volume: rows por run deixam de ser função da pausa. No run medido, 46
  ocorrências em **10** rows `(run, code, locator)` — contadas, não estimadas
  (o "~8" da versão `Proposto` era inferência). O cap
  `_REVIEW_REASON_ROW_CAP` segue defensivo.
- Retenção: `review_reasons.pipeline_run_id` é FK `ON DELETE CASCADE`
  ([[ADR-371]]) — a row morre com o run que a gerou. Nada a fazer.
- Rows históricas ficam com `locator` **vazio**, não nulo: a chave compara por
  igualdade e `NULL = NULL` é falso em SQL — locator nulo quebraria a
  idempotência do redelivery do Celery. `""` significa "não colhido".

## Deferimento 1 — superfície de usuário para aviso-sem-pausa (D4)

**Dono:** owner • **Condição:** decisão de produto sobre como o relatório mostra
aviso de run entregue. Até lá o aviso vive na tabela e no snapshot, e
`StageReview` segue exclusivo da pausa.

## Deferimento 2 — a poda por stage não alcança a tabela

**Dono:** `data-engineer` • **Medido 2026-08-25** (run `7164ddee`): **7 rows por
run**, contra 2 antes do D1. O eixo de **volume está refutado** — 7 rows de
diagnóstico não justificam política de expiração. O que sobra é semântico: depois
de um `reset_workspace_from_stage`, essas rows apontam por `artifact_key` para
artefato deletado. **Condição de retomada:** se algum leitor futuro resolver
`artifact_key` em vez de só exibi-lo. Hoje o único leitor é o
`review_snapshot`, que projeta `stage|locator|code` e **não** toca
`artifact_key` — logo o ponteiro morto não é observável por ninguém.
