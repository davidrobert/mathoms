---
id: A40.l76
type: lane
title: "A FK de proveniência do E2 nunca foi populada: o tombstone erra 630 rows e duas ADRs descrevem uma aresta vazia"
sprint: A40
status: open
priority: P1
branch_slug: a40-l76-proveniencia-de-artefato-e2
adrs:
  - "[[ADR-408]]"
  - "[[ADR-311]]"
  - "[[ADR-278]]"
  - "[[ADR-279]]"
  - "[[ADR-371]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/pipeline
  - area/db
---

# A40.l76 — Proveniência de artefato E2

> **Decisão já tomada:** [[ADR-408]] (`Proposto`, #1607) decide *como*, em co-design
> `data-engineer` + `senior-cto`. Esta lane é execução — não reabra o desenho. A
> [[ADR-311]] recebeu emenda datada (2026-08-21) dizendo o alcance real do D1.

> **Gate da lacuna já em `main`:** `backend/tests/test_artifact_tombstone.py`
> (#1600, `0ac274f3`) exercita os 2 stages com `xfail(strict=True)`. Quando a FK
> for populada os 4 casos passam, o marker falha e **força a própria remoção**.
> Não escreva gate novo para a mesma classe.

## Problema

`pipeline_artifacts.document_id` é NULL em **16.292/16.292** rows (dogfood,
re-medido 2026-08-21). A coluna, a FK (`ON DELETE SET NULL`) e o índice existem
desde [[ADR-082]]; `DBArtifactStore.write` aceita o parâmetro e **nenhum caller E2
passa** — `extract_with_llm.py:359,404` passa `document_id=None` literal.

Três consumidores degradam calados sobre a aresta vazia:

1. **Tombstone ([[ADR-311]] D1)** casa por FK **ou** por prefixo `<hash12>_`. Com a
   FK morta sobra o prefixo, ausente em `extract_informes_anuais` (0/282) e
   `extract_comprovantes_bens` (0/348): **630 rows** em que reclassificar deixa vivo
   o artefato do contrato antigo. Nesses dois a key é identidade de **entidade**
   ([[ADR-238]] D3 / [[ADR-239]] D7) — é desenho, não esquecimento.
2. **Lineage reverso ([[ADR-279]])** — `lineage_edge_writer.py:165-177` lê essa FK,
   logo toda edge `source_document` é NULL e `ix_artifact_lineage_edge_ws_doc`
   indexa constante. `report_lineage.py:57` já documenta o contorno em produção.
3. **[[ADR-278]]** planeja backfill "para artefatos E2 **com** `document_id`" —
   conjunto vazio. `data_source` tem **0 rows** e `data_source_id` é NULL em
   16.292/16.292 (medido).

## Escopo — quatro peças, ordem dura

A ordem não é preferência: a peça 1 é o que torna a peça 2 honesta.

1. **Guard de colisão** (pré-requisito). `UNIQUE(pipeline_run_id, stage,
   artifact_key)` + `_get` run-scoped fazem o segundo write cair em
   `row.document_id = document_id` — **último writer vence**. Com balde degenerado
   (`_unknown_`, `sem_numero`, `ano_desconhecido`) dois documentos colidem. Popular
   a FK **antes** disso produz ponteiro confiantemente errado: o tombstone passaria
   a deletar o artefato do documento errado. Hoje o NULL é honesto. A semântica de
   overwrite do `content_json` **não muda aqui** (defeito de desenho de key,
   anterior — [[ADR-407]] tratou o vizinho).
2. **Popular `document_id`** via porta `DocumentResolver` injetada em
   `WorkspaceContext` ([[ADR-408]] D1), chaveada por `stored_path` com fallback no
   prefixo do filename. **Nunca** por hash recomputado (D2). `≠1` match ⇒ NULL +
   contador, nunca adivinhar.
3. **Backfill das 630**, ops-gated, `--dry-run` default, sem reescrever
   `content_json` ([[ADR-408]] D6). Junção: `source_artifact_id` decriptado →
   prefixo → `documents.content_hash` workspace-scoped.
4. **Predicado de `orphan_document_candidates`**, no **mesmo PR** do backfill.
   `document_id IS NULL` colapsa três estados e o "documento deletado (SET NULL)"
   recomeça sozinho — o predicado nunca discriminou e não vai discriminar depois.

## Critério de aceite

- Os 4 casos de `test_tombstone_reaches_entity_keyed_e2_stages` passam e o
  `xfail(strict=True)` é **removido** no mesmo PR.
- **Regressão de documento destravado** — documento que passou por
  `try_unlock_pdf` resolve o `document_id` certo. Sem esse caso o fix é
  indistinguível do bug: o unlock reescreve o PDF **preservando o filename**
  (`document_processor.py:66-70`), e o hash de disco diverge de
  `documents.content_hash` em **3 de 6** comprovantes do dogfood — exatamente as 3
  apólices, a classe protegida por senha (medido 2026-08-21).
- Colisão de key por dois documentos no mesmo run emite sinal estruturado
  nomeando **ambos**; prova por mutação (remover o guard ⇒ teste vermelho).
- `lineage_edge_writer` produz edge `source_document` com id não-NULL — hoje 100%
  NULL.
- Backfill: dry-run reporta 630 resolvidos / 0 ambíguos antes do `--execute`;
  segunda execução encontra 0 (idempotência); `PRAGMA foreign_key_check` limpo;
  nenhum `content_json` alterado (`byte_size` e `prompt_version` inalterados).
- Telemetria `resolved`/`unresolved` por run. Sem ela o fix volta a falhar calado,
  que é a doença de origem.
- [[ADR-408]] flippa para `Decidido`.

## Fora de escopo

- **Estender a FK aos outros 7 stages E2.** Lá o prefixo já está na key e o
  tombstone funciona; é o passo que desbloqueia o backfill `kind='document'` da
  [[ADR-278]], mas é lane própria.
- **Reescrever [[ADR-278]] §Consequências e [[ADR-279]]**, que descrevem a aresta
  como viva. Ficam **registradas** na [[ADR-408]], não varridas — são notas de
  lanes alheias (precedente do #1597).
- **Semântica de overwrite do `content_json`** em colisão de key — ver peça 1.
