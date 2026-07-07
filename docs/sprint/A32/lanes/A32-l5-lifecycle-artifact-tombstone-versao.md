---
id: A32.l5
type: lane
title: "lifecycle de artifact E2: tombstone na reclassificação + versão de extração consultável (ADR-311)"
sprint: A32
plan: PLAN-data-lineage
status: planned
ship_pr: null
ship_date: null
priority: P1
branch_slug: a32-l5-artifact-lifecycle-tombstone
adrs: ["[[ADR-311]]", "[[ADR-278]]", "[[ADR-279]]", "[[ADR-281]]"]
depends_on: ["[[A32.l1]]"]
parallel_with: ["[[A32.l4]]"]
tags:
  - type/lane
  - sprint/a32
  - status/planned
  - priority/p1
  - area/pipeline
  - area/db
---

# A32.l5 — `artifact-lifecycle-tombstone` (fecha a raiz que re-envenena toda run)

## Problema

Artifacts E2 **nunca são invalidados**: nem quando o documento é
reclassificado (órfãos da l1), nem quando o writer/prompt evolui
(vocabulário stale de mai/jun). `_find_unprocessed_docs`
(`pipeline/stages/extract_with_llm.py:61-87`) pula key existente;
invalidação é só runbook manual (`extract_with_llm.py:461-462`) que o
dogfood provou que ninguém roda. Decisões fechadas em [[ADR-311]] —
**ler a ADR antes de codar**; esta lane operacionaliza. Escopo mínimo com
fronteira explícita com o plano [[PLAN-data-lineage|DATA_LINEAGE]]
(ADR-278–281 cobrem lineage; esta lane cobre só invalidação).

## Escopo

1. **Tombstone na reclassificação (escopo mínimo GARANTIDO da lane)** —
   reclassificar um documento (`POST /documents/reclassify` +
   `document_processor`) deleta os artifacts E2* daquele `document_id`
   nas stages downstream. Vive no backend adapter — respeita o boundary
   pipeline-sem-framework. Mata a classe dos órfãos na raiz.
2. **Versão de extração consultável** — `PROMPT_VERSION` (já gravado no
   payload, `extract_with_llm.py:266`) vira metadata/coluna consultável
   de `pipeline_artifacts` — **NUNCA na artifact_key** (quebraria dedupe
   por documento e forçaria re-extração total por bump de tuning).
   Migration Alembic leve: artifacts existentes → versão
   desconhecida/0. Teste com `pytestmark = pytest.mark.migration`.
3. **Script de re-extração DIRIGIDA** em `dev/` com `--dry-run` default
   (`WHERE stage='extract_with_llm' AND prompt_version < X`),
   ops-triggered. Usado pelo gate [[A32.l7]] para re-extrair os 11
   stale (decisão Q1 do owner). Re-extração AUTOMÁTICA em bump fica
   fora (owner-gated).
4. **Critério objetivo de recuo (PM):** se a metadata de versão exigir
   tocar tabelas `SourceRef`/`lineage_edge` ou o contrato de artifact da
   F1 do DATA_LINEAGE → a lane recua para **tombstone-only** + débito
   documentado na ADR. O tombstone nunca recua. Se recuar, a re-extração
   dos 11 no gate usa purga explícita por key (mesmo padrão da l1) em
   vez do script dirigido.

## Critérios de aceite

1. ADR-311 mergeada como Proposto ANTES do PR de impl; flip para
   `Decidido (A32.l5)` no merge.
2. Reclassificar um doc remove os artifacts E2* dele automaticamente
   (teste de regressão reproduzindo o cenário
   `cdbdetalhes→informe_previdencia` do dossiê).
3. Query lista artifacts E2-llm abaixo de versão-alvo; script dirigido
   testado em fixture sintética PII-zero.
4. Modo incremental (ADR-080) intacto;
   `backend/tests/integration/test_multi_worker_concurrency.py` verde
   (ADR-111).
5. `DB_SCHEMA_REFERENCE.md` regenerado se houver coluna nova. PR(s)
   mergeado(s) em `main` com CI verde.

## Arquivos load-bearing

| Arquivo | Papel |
|---|---|
| `pipeline/stages/extract_with_llm.py:61-87,266,461-462` | Skip por key existente + PROMPT_VERSION + runbook manual |
| `backend/app/services/db_artifact_store.py:336-347` | `list_keys` workspace-scoped |
| `backend/app/services/document_processor.py` + rota `reclassify` | Ponto do tombstone |
| `backend/app/services/internal_ops/pipeline_reset.py` | Padrão de invalidação destrutiva controlada |
| `docs/adr/311-lifecycle-artifact-e2-tombstone-reclassificacao.md` | Decisões fechadas |
