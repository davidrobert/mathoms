---
id: TRACK-a24-l7-schema-strict-flip
type: track
title: "Track A24.l7 — baseline → de-drift vocabulário E2 → flip strict per-schema"
lane: "[[A24.l7]]"
sprint: A24
status: ready
created_at: "2026-06-10"
agent_role: data-engineer
tags:
  - type/track
  - sprint/a24
  - status/ready
  - priority/p2
  - area/pipeline
  - area/observability
---

# Track A24.l7 — schema strict flip (follow-up ADR-284)

Self-contained: executável sem contexto da sessão de origem. Branch
`agent/schema-strict-flip/<ts>`. Pode virar 2–3 PRs (de-drift / gaps / flip).

## Contexto mínimo

- [[ADR-284]] entregou (PR #577): telemetria de drift (logger
  `mathoms.pipeline.schema_validation`, 1 WARNING por `validation_path`
  distinto com `workspace_id`), enforcement strict **real** no
  `DBArtifactStore` (raise; antes era no-op), `mode_overrides` per-schema em
  `config/pipeline.json`, corpus golden 22/22 em
  `tests/test_e2_schema_strict_corpus.py`.
- Procedimento operacional, queries de baseline, blast radius e rollback:
  [`docs/reference/runbooks/schema_validation_strict_flip.md`](../../../reference/runbooks/schema_validation_strict_flip.md).
- **Nada está em strict ainda** — `mode: warn` global; o flip é o entregável
  final desta track.

## Passos

### 1. Verificar baseline (gate, não-código)

Pré-requisito: commit `a2efb418` deployado em prod há ≥7 dias. Rodar as
queries do runbook §2 para **`e2_extract.schema.json` E
`e2_llm_artifact.schema.json`** (pós-[[ADR-285]] o ciclo tem 2 schemas, cada
um flippa independente). Go = **0 records** por schema. Drift inesperado
encontrado → corrigir writer ou declarar campo no schema (gate: corpus) e
reiniciar a janela daquele schema.

### 2. De-drift de vocabulário (bloqueador hard do flip) — ✅ entregue 2026-06-10

Resolvido em [[ADR-285]] (co-design `data-engineer`): cdbresumo emite `banco`
aditivo (valor = `instituicao`; zero downstream — E3 skipa cdbresumo, E4 lê
`instituicao or banco`); writer E2-llm **não foi tocado** (emitir `banco`/
`tipo` mudaria `AccountGrouper.key`/`from_e2_dict` → identidade E3, escopo
DATA_LINEAGE) — ganhou contrato dedicado `e2_llm_artifact.schema.json` com
transação compartilhada via `$ref e2_extract.schema.json#/$defs/transacao`
+ pin de resolução do `$ref`. `KNOWN_DRIFT_CASES == {}`.

### 3. INPUT_GAPS do corpus

5 parsers sem input sintético (`INPUT_GAPS` no corpus): PDFs de fatura
Carbon/Pão de Açúcar/Unique (estender gerador `tests/fixtures/pdf/`) e
2 XLS binários (escrita exige `xlwt`; alternativa aceita: cobrir via
baseline zero-WARN nos tipos correspondentes, runbook §1.2, e registrar
aceite no §7).

### 4. Flip + verificação + alerta

Runbook §3 (PR de 1 linha em `mode_overrides`), §4 (janela 48h/10 runs),
§5 (rollback com gatilho objetivo), §7 (registrar histórico). Depois do
primeiro flip estável: criar alerta ticket (não page) em rate>0/1h.

## Critério de aceite

- `KNOWN_DRIFT_CASES == {}` e corpus verde em strict.
- Linha no runbook §7 com flip de `e2_extract.schema.json` sem rollback.
