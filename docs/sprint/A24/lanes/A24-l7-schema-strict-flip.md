---
id: A24.l7
type: lane
title: "Schema strict flip — baseline → de-drift de vocabulário → flip E2 (ADR-284)"
sprint: A24
status: open
priority: P2
branch_slug: schema-strict-flip
adrs:
  - "[[ADR-284]]"
  - "[[ADR-283]]"
prompt: "[[TRACK-a24-l7-schema-strict-flip]]"
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a24
  - status/open
  - priority/p2
  - area/pipeline
  - area/observability
---

# A24.l7 — `schema-strict-flip` (débito/ops, fora do tema data-lineage)

> Follow-up operacional da [[ADR-284]] (mergeada em PR #577, 2026-06-10).
> O mecanismo (telemetria + `mode_overrides` + enforcement strict real +
> corpus 22/22) está em `main`; esta lane executa a sequência até o flip
> de `e2_extract.schema.json` para `strict` em prod.
> Runbook dono: [`schema_validation_strict_flip.md`](../../../reference/runbooks/schema_validation_strict_flip.md).

## Sequência (gates em ordem)

1. **Baseline 7d** — começa no deploy de `a2efb418` em prod. Check agendado
   ~2026-06-17: rodar queries do runbook §2 (go = 0 WARN p/ `e2_extract`).
2. **De-drift de vocabulário (bloqueador hard)** — ✅ **entregue 2026-06-10**
   ([[ADR-285]], co-design `data-engineer`): cdbresumo emite `banco` aditivo
   (valor = `instituicao`); writer E2-llm ganhou contrato dedicado
   `e2_llm_artifact.schema.json` (vocabulário próprio explícito; tocar o
   writer mudaria identidade E3 — canonicalização é follow-up do plano
   [[PLAN-data-lineage]]). Bucket `KNOWN_DRIFT_CASES` vazio; transação
   compartilhada via `$ref` com pin de resolução.
   **Consequência p/ o passo 1:** o baseline passa a ter **2 schemas** no
   ciclo — `e2_extract` e `e2_llm_artifact` (cada um flippa independente).
3. **INPUT_GAPS** — layouts sintéticos p/ 3 PDFs de fatura (Carbon, Pão de
   Açúcar, Unique); decidir os 2 XLS binários (xlwt ou aceitar via baseline
   zero-WARN nos tipos correspondentes, runbook §1.2).
4. **Flip** — PR de 1 linha (`mode_overrides`), procedimento runbook §3,
   verificação §4, rollback §5. Registrar no §7 (histórico).
5. **Alerta pós-flip** — ticket (não page) em rate>0/1h p/ o schema flipado.
   Só depois do primeiro flip (criar antes é threshold inventado).

## Critério de aceite da lane

- Linha preenchida no runbook §7 com flip de `e2_extract.schema.json` sem
  rollback na janela de 48h/10 runs (§4).
