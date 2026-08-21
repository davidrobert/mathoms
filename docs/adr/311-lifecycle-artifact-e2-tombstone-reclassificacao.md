---
id: ADR-311
type: adr
title: "Lifecycle de artifact E2: tombstone por reclassificação + versão de extração consultável"
status: Decidido
phase: A32.l5
date: "2026-07-07"
amended_at: ["2026-08-21"]
relates_to: ["[[ADR-278]]", "[[ADR-279]]", "[[ADR-281]]", "[[ADR-212]]", "[[ADR-080]]", "[[ADR-408]]"]
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/db
---

# ADR-311 — Lifecycle de artifact E2: tombstone por reclassificação + versão de extração consultável

**Status:** Decidido (A32.l5) · **Data:** 2026-07-07

> **Emenda de alcance ([[ADR-408]], 2026-08-21):** o D1 abaixo descreve o
> tombstone como "restrito por `workspace_id + document_id + stage`". Medido no
> dogfood, `pipeline_artifacts.document_id` é NULL em **16.292/16.292** rows —
> esse caminho nunca casou. Quem entrega o D1 hoje é um segundo predicado que
> esta ADR não menciona (prefixo `<content_hash[:12]>_` na key), e ele **não
> alcança 2 dos 6 stages** de `_E2_DESCRIPTIVE_STAGES`. A decisão do D1
> permanece; o alcance dela era menor do que o texto afirma. Ver §Emenda.

## Contexto

Artifacts E2 em `pipeline_artifacts` ([[ADR-212]]) **nunca são
invalidados**: `_find_unprocessed_docs`
(`pipeline/stages/extract_with_llm.py:61-87`) pula qualquer doc cuja key
já exista; invalidação é runbook manual (`extract_with_llm.py:461-462`);
a leitura é workspace-scoped (`db_artifact_store.py:336-347`). Dogfood
2026-07-07: 11 artifacts E2-llm de mai/jun com vocabulário stale
(`instituicao` sem `banco`) + 2 órfãos de documentos reclassificados
continuavam envenenando **toda** run, semanas depois dos fixes de writer.
O runbook manual provou-se letra morta. Co-design 2026-07-07:
`senior-cto` + `data-engineer` + `prompt-engineer` + `sre-devops` (custo).

Fronteira: [[ADR-278]]–[[ADR-281]] (plano DATA_LINEAGE) cobrem lineage
forward/reverso e `SourceRef`. Esta ADR cobre **somente invalidação** —
escopo mínimo.

## Decisão

1. **Tombstone na reclassificação** — reclassificar um documento
   (`POST /documents/reclassify` + `document_processor`) deleta os
   artifacts E2* daquele `document_id` nas stages downstream, restrito
   por `workspace_id + document_id + stage`. Implementado no backend
   adapter (pipeline não importa framework). Mata a classe dos órfãos na
   raiz.
2. **Versão de extração como metadata consultável, nunca na key** —
   `PROMPT_VERSION` (já presente no payload, `extract_with_llm.py:266`)
   vira coluna/metadata de `pipeline_artifacts`, consultável por SQL.
   Na artifact_key seria errado: quebraria o dedupe por documento e
   forçaria re-extração total a cada bump de tuning (convergência
   `prompt-engineer` + `senior-cto` uma vez separado "onde armazena" de
   "quando re-extrai").
3. **Re-extração DIRIGIDA, ops-triggered** — script em `dev/` com
   `--dry-run` default (`WHERE stage='extract_with_llm' AND
   prompt_version < X`). Re-extração **automática** em bump de versão
   fica explicitamente fora — política de custo LLM é decisão do owner
   (cap [[ADR-173]]).
4. **Migration leve** — artifacts existentes recebem versão
   desconhecida/0; sem backfill de conteúdo.
5. **Critério objetivo de recuo** — se a metadata de versão exigir tocar
   tabelas `SourceRef`/`lineage_edge` ou o contrato de artifact da F1 do
   DATA_LINEAGE, a lane recua para tombstone-only e o item 2 vira débito
   documentado nesta ADR. O tombstone (item 1) não recua.

## Consequências

- Reclassificação passa a ter efeito destrutivo downstream (era o
  comportamento esperado que faltava); re-run pós-reclassificação
  re-extrai sob o contrato novo.
- Modo incremental ([[ADR-080]]) intacto: mesma (doc, versão) → mesma
  key → mesmo objeto; idempotência entre workers ([[ADR-111]]) preservada.
- Custo LLM de re-extração só quando disparado explicitamente (dirigido).
- Débito de artifacts stale deixa de acumular silencioso; o restante do
  lifecycle (retenção, lineage) permanece no DATA_LINEAGE.

## Emenda 2026-08-21 — o D1 é no-op em 2 dos 6 stages E2*

`_document_match_conditions` casa por FK **ou** por prefixo `<hash12>_`. A FK
está morta (16.292/16.292 NULL; nenhum caller E2 popula, e
`extract_with_llm.py:359,404` passa `document_id=None` literal), então o
prefixo é o predicado efetivo. Ele cobre 100% de `extract_statements` (2943),
`extract_invoices` (1502), `extract_irpf_full` (404), `E1.5a` (786),
`extract_informe_aluguel` (206) e `extract_with_llm` (33) — e **0/282 de
`extract_informes_anuais`** e **0/348 de `extract_comprovantes_bens`**.

**Por que esses dois, e por que não é esquecimento.** Neles o `artifact_key` é
identidade de **entidade** derivada do payload extraído — `crlv_<placa>_<ano>`
e `apolice_<numero>_<ano>` ([[ADR-239]] D7), `<tipo>_<instituicao>_<ano>`
([[ADR-238]] D3). Não há hash de documento na key porque a key não endereça
documento. **630 rows** ficam fora do alcance: reclassificar deixa vivo o
artifact do contrato antigo, que é exatamente a classe que o D1 existe para
matar.

Corolário do próprio D2 desta ADR: se pôr `PROMPT_VERSION` na key "quebraria o
dedupe por documento", pôr o hash do documento numa key que endereça entidade
quebra a supersessão por entidade — `list_latest_keys` faz latest-wins por key,
e fragmentá-la faz `InformeQuery._fetch_payloads` devolver todas as versões
(dupla contagem na cascata fiscal). O eixo de proveniência é **coluna**, não
key. O fix está em [[ADR-408]].

Gate da lacuna: `backend/tests/test_artifact_tombstone.py` passou a exercitar os
dois stages com as formas reais de key (`xfail(strict=True)` — vira verde e
força a remoção do marker quando a FK for populada).

## Alternativas rejeitadas

- **Versão na artifact_key:** quebra dedupe por documento; re-extração
  total forçada a cada bump; polui a key (rejeição `prompt-engineer`).
- **Leitura run-scoped:** quebraria o modo incremental (ADR-080) e a
  economia de não re-extrair; custo LLM explode (rejeição `senior-cto`).
- **Big-bang `extractor_version=0` forçando re-extração geral na próxima
  run:** re-extrai antes da purga de órfãos e re-envenena; custo não
  dirigido (resolução do conflito no co-design — purga cirúrgica venceu).
- **Manter só o runbook manual:** o dogfood provou que não roda; débito
  acumula silencioso.
