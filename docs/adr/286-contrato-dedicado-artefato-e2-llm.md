---
id: ADR-286
type: adr
title: "Contrato dedicado para o artefato E2-llm (e2_llm_artifact.schema.json) + banco aditivo em cdbresumo"
status: Decidido
phase: "A24.l7"
date: "2026-06-10"
relates_to:
  - "[[ADR-284]]"
  - "[[ADR-282]]"
  - "[[ADR-280]]"
supersedes: []
superseded_by: []
aliases: ["ADR 286", "e2 llm artifact schema", "vocabulario dual e2"]
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/data-lineage
---

# ADR-286 — Contrato dedicado para o artefato E2-llm + banco aditivo em cdbresumo

**Status:** Decidido (A24.l7) • **Data:** 2026-06-10 • **Relaciona**
[[ADR-284]] (flip strict per-schema — este é o de-drift do gate),
[[ADR-282]] (identidade de override — por que não tocar o writer LLM),
[[ADR-280]] (de-leak — onde a canonicalização pertence).

## Contexto

O corpus da [[ADR-284]] pinou 3 writers violando `required` do
`e2_extract.schema.json` — bloqueadores do flip strict de E2:

1. **cdbresumo (Itaú HTML-XLS + Santander XLSX)** emitem `instituicao`, não
   `banco`. Verificado: payload sem `transacoes` (nada a estampar), E3 skipa
   `cdbresumo` via `skip_types` **antes** do grouping, e E4 lê
   `instituicao or banco` — presença de `banco` não é discriminador em nenhum
   call-site.
2. **Writer E2-llm** (`_output_to_e2_json`) emite `instituicao`/`tipo_documento`
   sem `banco`/`tipo`. Aqui emissão aditiva **não** é inócua: statements LLM
   hoje atravessam o E3 com `tipo=""` (logo `AccountGrouper.key() → None`) e
   `BankStatement.institution=""`; adicionar os campos flipa grouping,
   `artifact_key` e identidade de artefatos E3 — churn que [[ADR-282]] trata
   com rebaseline controlado no plano DATA_LINEAGE, fora desta lane.

## Decisão

1. **cdbresumo: `banco` aditivo** nos 2 parsers, valor idêntico a
   `instituicao`. Cases promovidos a `PASS_CASES` no corpus.
2. **E2-llm: contrato dedicado** `config/schemas/e2_llm_artifact.schema.json`
   (`required: instituicao, tipo_documento, moeda`; top-level aberto);
   `SCHEMA_BY_STAGE["E2-llm"/"extract_with_llm"]` remapeado. O schema passa a
   descrever a realidade do writer — a dualidade de vocabulário **já existia**;
   ela vira contrato explícito e versionado em vez de violação mascarada.
3. **Sub-contrato de transação compartilhado por `$ref`** —
   `e2_extract.schema.json` ganha `$id` + `$defs/transacao`;
   `e2_llm_artifact` referencia `e2_extract.schema.json#/$defs/transacao`
   (precedente: família `informe_*`). Cópia criaria exatamente o drift que o
   gate existe para impedir. Pin obrigatório: teste que prova a **resolução**
   do `$ref` (em modo `warn`, `Unresolvable` degrada para WARN silencioso —
   um typo de `$id` deixaria o gate verde até o flip).

## Não-decisões (adiadas)

- **Canonicalizar o vocabulário do writer LLM** (emitir `banco`/`tipo`) —
  adiado para o plano [[PLAN-data-lineage]] (registrado em §Ondas/follow-ups):
  muda `AccountGrouper.key`/`from_e2_dict` → identidade E3, que lá é tratada
  com golden substrate + rebaseline manifestado. Não pertence a uma lane de
  validação.

## Consequências

- `KNOWN_DRIFT_CASES` do corpus esvazia — gate de vocabulário do flip de
  `e2_extract.schema.json` fechado ([[ADR-284]] §E).
- `e2_llm_artifact.schema.json` entra no ciclo do runbook
  [`schema_validation_strict_flip.md`](../reference/runbooks/schema_validation_strict_flip.md)
  com baseline/flip **próprios**.
- Zero mudança de execução: goldens E3 + suites LLM verdes sem rebaseline
  (remap é só validação pós-write).

## Critério de aceite

- Corpus: 17 `PASS_CASES` (15 + 2 cdb) contra `e2_extract`; writer LLM PASS em
  strict contra `e2_llm_artifact`; teste de `$ref` resolvido (drift
  `additionalProperties` em `$.transacoes[].x` + sem WARN `unresolvable`).
- `tests/test_e3_golden_execution.py` + `tests/test_llm_stages*.py` verdes sem
  rebaseline.
