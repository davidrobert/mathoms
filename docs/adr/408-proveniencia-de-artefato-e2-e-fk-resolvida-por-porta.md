---
id: ADR-408
type: adr
title: "Proveniência de artefato E2 é FK resolvida por porta injetada, não hash recomputado nem prefixo de key"
status: Proposto
date: "2026-08-21"
relates_to: ["[[ADR-311]]", "[[ADR-278]]", "[[ADR-279]]", "[[ADR-371]]", "[[ADR-238]]", "[[ADR-239]]", "[[ADR-212]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 408", "FK document_id", "proveniência de artefato E2"]
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/db
---

# ADR-408 — Proveniência de artefato E2 é FK resolvida por porta injetada, não hash recomputado nem prefixo de key

**Status:** Proposto · **Data:** 2026-08-21

## Contexto

`pipeline_artifacts.document_id` é NULL em **16.292/16.292** rows do dogfood
(2026-08-21), em todos os 24 nomes de stage. A coluna, a FK
(`ON DELETE SET NULL`) e o índice `ix_pipeline_artifacts_document_id` existem
desde [[ADR-082]]; `DBArtifactStore.write` aceita `document_id` e nenhum caller
E2 passa — o call-site é `extract_with_llm.py:314`
(`store.write("extract_with_llm", safe_stem, e2_json)`), que **omite** o kwarg.

> ⚠️ **Não confundir com `:359,404` (auditoria r10 · F08).** Essas duas linhas
> são `document_id=None` dentro de `ReviewReason`, e o comentário logo acima
> de `:404` registra que preencher ali **viola a FK** — foi exatamente o que o
> #1535 fechou ([[ADR-371]]). A §Decisão 1 vale para `:314`; mexer em
> `:359,404` reintroduz o defeito.

**Três consumidores degradam calados sobre essa aresta vazia:**

1. **[[ADR-311]] D1** — o tombstone casa por FK **ou** por prefixo
   `<content_hash[:12]>_`. Com a FK morta, sobra o prefixo, que não existe em
   `extract_informes_anuais` (0/282) nem `extract_comprovantes_bens` (0/348):
   **630 rows** em que reclassificar não invalida nada. Ver §Emenda da ADR-311.
2. **[[ADR-279]]** — `lineage_edge_writer.py:165-177` popula
   `ArtifactLineageEdge.source_document_id` lendo essa FK; logo toda edge
   `source_document` é NULL e `ix_artifact_lineage_edge_ws_doc` indexa
   constante. `report_lineage.py:57` já documenta o contorno em produção
   ("DISTINCT `artifact_key` em stages E2 — **proxy** de docs extraídos").
3. **[[ADR-278]]** — §Consequências planeja "backfill idempotente
   `kind='document'` para artefatos E2 **com `document_id`**": conjunto vazio.
   `data_source` tem 0 rows e `data_source_id` é NULL em 16.292/16.292. A folha
   que a porta `SourceAdapter` generaliza não existe.

Co-design 2026-08-21: `data-engineer` + `senior-cto`, convergentes.

## Decisão

1. **A proveniência é a FK, resolvida por porta injetada.** `DocumentResolver`
   entra em `WorkspaceContext` (padrão de dez portas já existentes:
   `property_identity_resolver` [[ADR-215]], `economic_assumptions_resolver`
   [[ADR-219]], `institution_catalog_provider`…), devolve `SourceRef | None`
   (`pipeline/domain/ports/source.py`, vocabulário já decidido na [[ADR-278]]),
   com implementação em `backend/app/services/` e wiring em
   `_setup_run_context`. O stage passa `document_id=` explícito ao
   `store.write`. **O `ArtifactStore` Protocol não muda** e
   `InMemoryArtifactStore.document_id_for` continua sendo a asserção de domínio
   testável sem DB.
2. **A chave de resolução é `stored_path` (fallback: prefixo `<hash12>_` do
   filename), nunca hash recomputado do arquivo em disco.** `try_unlock_pdf`
   salva o PDF destravado e faz `tmp.rename(path)` — reescreve os bytes
   **preservando o filename** (`document_processor.py:66-70`,
   `unlock_documents.py:139-141`). Logo `_content_hash(doc)`
   (`extract_informes_anuais.py:367`) é o hash pós-unlock e diverge de
   `documents.content_hash` em todo documento que teve senha (3 de 6
   comprovantes no dogfood). Resolver por ele passa no corpus sem senha e falha
   **calado** exatamente na classe protegida — onde moram extratos e faturas.
3. **Prefixo de hash na key desses dois stages é rejeitado** — ver §Alternativas.
4. **A FK só é populada quando a resolução é inequívoca.** `≠1` match ⇒ NULL +
   contador, nunca adivinhar. Idem colisão: `UNIQUE(pipeline_run_id, stage,
   artifact_key)` + `_get` run-scoped fazem o segundo write cair em
   `row.document_id = document_id` — **último writer vence**. Com key de
   entidade degenerada (`_unknown_`, `sem_numero`, `ano_desconhecido`) dois
   documentos colidem, e uma FK confiantemente errada é **pior que o NULL de
   hoje**: o tombstone passaria a deletar o artefato do documento errado. A
   colisão emite sinal estruturado; a semântica de overwrite do `content_json`
   **não muda aqui** (é defeito do desenho de key, anterior a esta ADR).
5. **`ON DELETE SET NULL` permanece — e a escolha passa a ser load-bearing.**
   Hoje é no-op (tudo já é NULL). `CASCADE` faria a deleção de um documento
   atravessar até o substrato de relatório publicado, a classe que [[ADR-371]]
   D3 fecha; `RESTRICT` deixaria `delete_document` inoperante em todo documento
   que já produziu artefato. `delete_document` reporta `artifacts_unlinked`
   (ADR-371 D5: preservar sem avisar é o mesmo erro de apagar sem avisar).
6. **Backfill é ops-gated e fora do caminho de deploy** — `--dry-run` default,
   mutação restrita por id, **sem reescrever `content_json`** (forma de
   `dev/purge_orphan_e2_artifacts.py`). A junção sobrevive à cifragem via
   `source_artifact_id` decriptado → prefixo → `documents.content_hash`
   workspace-scoped. O predicado de `orphan_document_candidates` muda **no mesmo
   PR** do backfill: `document_id IS NULL` colapsa "nunca populado", "documento
   deletado (SET NULL)" e "órfão real", e o segundo recomeça sozinho — logo o
   predicado nunca discriminou e não vai discriminar depois.

## Consequências

- A aresta `documento → artifact` passa a existir para os três consumidores; o
  proxy por `artifact_key` em `report_lineage` deixa de ser necessário.
- `ix_pipeline_artifacts_document_id` deixa de ser custo de escrita sobre coluna
  constante.
- Nenhuma migration de DDL: coluna, FK e índice já existem.
- O resolver falha **aberto** (`None` ⇒ FK NULL ⇒ comportamento de hoje). O modo
  de falha é o status quo, não uma regressão — por isso a telemetria
  `resolved`/`unresolved` por run é parte da decisão, não polimento: sem ela o
  fix volta a falhar calado, que é a doença de origem.
- As keys de [[ADR-238]] D3 e [[ADR-239]] D7 ficam **confirmadas**, não
  revertidas.

## Alternativas rejeitadas

- **Prefixar `<hash12>_` na key de `extract_informes_anuais` /
  `extract_comprovantes_bens`.** A key é o endereço de supersessão
  (`list_latest_keys` faz latest-wins); prefixá-la converte "última extração do
  informe Itaú 2025" em N artefatos coexistentes, e
  `InformeQuery._fetch_payloads` devolve **todos** ⇒ dupla contagem na cascata
  fiscal. Quebra também `protecao_wiring.py:47`
  (`k.startswith("apolice_")` ⇒ bundle de proteção vazio, calado). Trocaria
  perda silenciosa por soma dobrada silenciosa; num relatório financeiro a
  segunda é pior. É o argumento do D2 da [[ADR-311]] aplicado ao outro eixo.
- **Resolver dentro de `DBArtifactStore.write`** (store recebe `content_hash` e
  faz o SELECT). Esconde I/O por artefato no caminho de lock mais quente
  ([[ADR-256]]), quebra a asserção de domínio `document_id_for` — o
  `InMemoryArtifactStore` guardaria hash e o `DBArtifactStore` guardaria id — e,
  decisivo, **não funciona**: o hash disponível ao store é o pós-unlock (D2). O
  precedente da [[ADR-239]] D3 não sustenta: ele autoriza *aquele* stage a
  alcançar o DB para reconciliação do agregado que ele possui, não a buscar
  contexto de run, que neste repo é injetado.
- **Trocar a FK por `source_content_hash`.** Seria a terceira coluna de
  proveniência ao lado de `document_id` e `data_source_id`, exigindo supersedure
  da [[ADR-278]]; e é estritamente mais fraca — não junta com `documents` para o
  escopo `workspace_id + documento` do tombstone, e não sobrevive a re-upload do
  mesmo conteúdo sob id novo.
- **Fechar as 630 com `LIKE` sobre `content_json->>'source_artifact_id'`.**
  Fecharia o sintoma do tombstone em ~10 linhas e deixaria de pé os outros dois
  consumidores; além disso o payload é cifrado, logo não é queryável em SQL.
