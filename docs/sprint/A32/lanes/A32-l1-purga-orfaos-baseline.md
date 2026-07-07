---
id: A32.l1
type: lane
title: "purga de artifacts E2-llm órfãos + snapshot baseline da run dogfood d1732edd"
sprint: A32
plan: null
status: shipped
ship_pr: 825
ship_date: "2026-07-07"
priority: P0
branch_slug: a32-l1-purge-orphan-baseline
adrs: []
depends_on: []
parallel_with: ["[[A32.l2]]", "[[A32.l3]]"]
tags:
  - type/lane
  - sprint/a32
  - status/shipped
  - priority/p0
  - area/pipeline
  - area/db
---

# A32.l1 — `purge-orphan-baseline` (purga cirúrgica + baseline instrumentado)

## Problema

2 artifacts E2-llm são **órfãos de reclassificação**: os documentos foram
reclassificados para `informe_previdencia_privada` (processados por
E1.5a), mas o artifact E2-llm sob a key antiga sobrou em
`pipeline_artifacts` e envenena o E3 a cada run —
`_find_unprocessed_docs` (`pipeline/stages/extract_with_llm.py:61-87`)
pula docs cuja key já existe, e `DBArtifactStore.list_keys` é
workspace-scoped (`backend/app/services/db_artifact_store.py:336-347`).
Além deles, 11 artifacts E2-llm de mai/jun têm vocabulário stale
(`instituicao` sem `banco`). Sem baseline congelado, os KRs da sprint não
são mensuráveis.

## Escopo

1. **Script idempotente dry-run-first** em `dev/`
   (`dev/purge_orphan_e2_artifacts.py` ou similar):
   - `--dry-run` default; execução real exige flag explícita.
   - Deleta **somente** os 2 artifacts órfãos de reclassificação,
     restrito por `workspace_id + document_id + stage` — impossível
     deletar além do alvo por construção.
   - **Lista (sem deletar)** os 11 artifacts institution-vazio de
     mai/jun. Decisão Q1 do owner (2026-07-07): esses 11 serão
     **re-extraídos via LLM** após a l2 (contrato novo), pelo script
     dirigido da [[A32.l5]] — não são purgados aqui.
2. **Snapshot baseline** da review da run `d1732edd` (18 errors + 31
   warnings, contagem por `code`) formalizado na tabela do
   [[MOC-sprint-a32]] — é a régua de KR1/KR2/KR4.
3. **Sem re-extração LLM nesta lane** — re-run medido acontece só no gate
   ([[A32.l7]]), depois dos fixes de código; re-run antes dos fixes
   mostraria os mesmos erros e queimaria a segunda impressão do owner.

## Critérios de aceite

1. Dry-run lista exatamente 2 órfãos (delete) + 11 stale (report-only)
   antes de qualquer mutação; saída do dry-run colada no PR.
2. Após execução: os 2 órfãos ausentes de `pipeline_artifacts`; os 11
   intactos.
3. Baseline por code commitado no `_README.md` da sprint.
4. Script coberto por teste com fixture sintética PII-zero
   (`InMemoryArtifactStore` ou SQLite in-memory; DB nunca mocado).
5. PR mergeado em `main` (squash) com CI verde.

## Arquivos load-bearing

| Arquivo | Papel |
|---|---|
| `pipeline/stages/extract_with_llm.py:61-87` | `_find_unprocessed_docs` — por que órfão nunca se auto-corrige |
| `backend/app/services/db_artifact_store.py:336-347` | `list_keys` workspace-scoped |
| `backend/app/services/internal_ops/pipeline_reset.py` | Padrão existente de mutação destrutiva controlada |
| `docs/sprint/A32/_README.md` | Destino do baseline |
