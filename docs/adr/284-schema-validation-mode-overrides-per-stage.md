---
id: ADR-284
type: adr
title: "Schema validation: mode_overrides per-schema, enforcement strict real e telemetria de drift"
status: Proposto
phase: "Débito técnico"
date: "2026-06-09"
relates_to:
  - "[[ADR-283]]"
  - "[[ADR-212]]"
  - "[[ADR-242]]"
  - "[[ADR-278]]"
supersedes: []
superseded_by: []
aliases: ["ADR 284", "schema mode overrides", "strict flip per-stage", "schema drift telemetry"]
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/backend
  - area/observability
---

# ADR-284 — Schema validation: mode_overrides per-schema, enforcement strict real e telemetria de drift

**Status:** Proposto (Débito técnico) • **Data:** 2026-06-09 • **Relaciona**
[[ADR-283]] (decisão D + §Follow-ups #3), [[ADR-212]] (hook pós-write),
[[ADR-242]] (categoria_sugerida), [[ADR-278]] (amount/natural_key).

## Contexto

[[ADR-283]] fechou `transacoes.items.additionalProperties:false` no schema E2 e
adiou o flip `warn→strict` para uma lane de telemetria/ops. A auditoria desta
lane encontrou que a fundação do flip não existia:

1. **Strict era no-op no caminho de produção.** `DBArtifactStore._validate_schema`
   (staticmethod) descartava o bool de `validate_dict`; `_handle_validation_error`
   retornava `False` sem raise. A docstring de `SCHEMA_BY_STAGE` ("strict propaga
   ValidationError") era aspiracional. O branch `outcome=="raised"` em
   `test_db_artifact_store_pii_encryption.py` nunca rodava no CI (job strict cobre
   só `tests/test_schema_validation.py`, que testa `validate_dict` direto).
2. **WARN de validação não tinha telemetria.** `log_stage` texto-plano, sem
   `workspace_id` (contextvars de correlação não são setadas em Celery), parava
   no 1º erro (`validator.validate`) e **vazava o valor ofensor** — `exc.message`
   do jsonschema embute a instância (ex.: `'9876.54' is not of type 'string'`),
   furando a regra de PII monetária (redaction por key não pega valor dentro de
   message).
3. **O contrato E2 não refletia os writers vivos.** O audit da ADR-283 cobriu os
   parsers de `scripts/e2/banks/` mas não o writer LLM (`_output_to_e2_json`),
   que emite `categoria_sugerida` ([[ADR-242]]) e `saldo_apos` por transação —
   ambos não-declarados no contrato fechado. `required` exigia `pipeline_stage`,
   que **nenhum** writer E2 estampa (vestígio da era disco; pós-[[ADR-212]] o
   stage é coluna do DB) — todo write E2 em prod geraria WARN de ruído.
4. **Drift de vocabulário real**: cdbresumo (Itaú/Santander) e o writer E2-llm
   emitem `instituicao`/`tipo_documento` em vez de `banco`/`tipo` — violação
   genuína de required que **abortaria todo write E2-llm** num flip strict.

## Decisão

### A — Enforcement strict real no `DBArtifactStore`

`_validate_schema` vira instance method; `validate_dict→False` em strict →
**raise `jsonschema.ValidationError`** e o write não acontece (dado não
corrompe; o run falha naquele stage para aquele workspace). Guarda de retry em
`_run_stage_with_retry`: `ValidationError` é **não-retryable incondicional** —
erro de contrato é determinístico; sem a guarda, stages com `retryable_errors`
(E2-llm) casariam substring do texto do erro e queimariam backoff inútil.

### B — Telemetria estruturada de drift (log-only)

Logger novo `mathoms.pipeline.schema_validation`, 1 record WARNING por
**path distinto** (dedup por `(validation_path, validator)` com
`occurrence_count`; cap de 20 paths como teto de segurança), com
`extra={workspace_id, pipeline_run_id, stage, artifact_key, schema_name,
validation_path, validator_keyword, mode, outcome}`. Contexto vem por
threading explícito do `DBArtifactStore` (`validate_dict(..., context=...)`).
`validation_path` é normalizado — índices de array viram `[]`
(`$.transacoes[].x`, cardinalidade bounded p/ agregação); erros
`additionalProperties`/`required` expandem para 1 path por campo
extra/faltante (nome de campo é metadado, não PII). **Nunca** loga
`error.message`/`error.instance`. `iter_errors` substitui `validate`
(baseline sem undercount). Baseline = agregação dos logs JSON; sem tabela DB,
sem métrica OTel (volume dezenas/dia, go/no-go manual).

### C — `mode_overrides` per-schema

`pipeline.json → schema_validation.mode_overrides` keyed por **filename de
schema** (`"e2_extract.schema.json": "strict"`) — não por stage: cobre os 7
stage-aliases E2 do `SCHEMA_BY_STAGE` de uma vez e `validate_dict` conhece
`schema_name`, não stage. Precedência: env `MATHOMS_PIPELINE_SCHEMA_MODE`
(global, CI/escape) > `mode_overrides[schema]` > `mode`. Typo de key é gate de
teste (`test_mode_overrides_do_repo_referenciam_schemas_existentes`) +
`propertyNames` no `pipeline.schema.json`.

### D — Contrato E2 corrigido para os writers vivos

`e2_extract.schema.json`: (a) `pipeline_stage` sai do `required` (nenhum writer
estampa; manter geraria ruído permanente no baseline); (b) declara
`categoria_sugerida`, `saldo_apos` (writer LLM) e `tipo` (santander fatura CSV)
em `transacoes.items.properties`. O drift de vocabulário top-level
(`banco`/`tipo` vs `instituicao`/`tipo_documento` em cdbresumo + E2-llm) **não**
é acomodado no schema — é violação real, pinada pelo corpus, bloqueadora do flip.

### E — Corpus golden 22/22 como gate do flip

`tests/test_e2_schema_strict_corpus.py`: enumeração exaustiva das 22 funções de
parser registradas (meta-teste falha se parser novo entrar sem decisão de
corpus) em 3 buckets — 15 `PASS_CASES` (real-parse sintético + `stamp_natural_key`,
espelho do write-path de prod, valida em strict), 3 `KNOWN_DRIFT` (cdbresumo
Itaú/Santander + writer E2-llm; paths exatos pinados), 5 `INPUT_GAPS` (PDFs de
fatura sem layout sintético; XLS binário sem xlwt). Flip de E2 exige bucket
KNOWN_DRIFT vazio + INPUT_GAPS coberto ou aceito explicitamente (runbook).

## Não-decisões (rejeitadas / adiadas)

- **Tabela DB / métrica OTel para o contador** — over-engineering para
  dezenas de eventos/dia com decisão go/no-go manual. Alerta automático é
  follow-up pós-flip (ticket, não page).
- **Keying de `mode_overrides` por stage** — frágil: exigiria enumerar e
  sincronizar os aliases de `SCHEMA_BY_STAGE`.
- **Acomodar `instituicao`/`tipo_documento` no schema** (anyOf) — esconderia
  divergência real de vocabulário entre famílias de writer; resolução é
  normalizar o writer (ou schema dedicado p/ cdbresumo), não afrouxar o contrato.
- **Flipar strict nesta lane** — o flip é operacional, gated por baseline ≥7
  dias zero-WARN para o schema alvo (runbook
  [`schema_validation_strict_flip.md`](../reference/runbooks/schema_validation_strict_flip.md)).

## Consequências

- Flip per-schema vira possível e reversível em 1 linha de config; strict
  passa a **bloquear de verdade** (e só onde flipado).
- Baseline de drift por workspace/stage/path consultável nos logs JSON.
- Drift conhecido (cdbresumo, E2-llm) documentado e pinado — flip de E2
  bloqueado até resolver, em vez de descoberto em produção via run abortado.
- Custo: zero mudança de comportamento em prod nesta lane (`mode: warn`
  intocado; raise só dispara em strict, e nada está em strict).

## Critério de aceite

- Strict env: write inválido em `DBArtifactStore` raise `ValidationError`;
  warn: persiste + record de drift com `workspace_id`.
- `mode_overrides` per-schema: rejeita só o schema alvo; env global vence;
  key órfã falha gate de teste.
- `ValidationError` em stage com `retryable_errors` não dorme backoff.
- Telemetria: dedup por path (3 erros mesmo path → 1 record, count=3); valor
  sentinela da instância **não** aparece em `caplog.text`.
- Corpus: 22/22 funções enumeradas; 15 PASS em strict; drift pinado nos 3
  writers divergentes.
