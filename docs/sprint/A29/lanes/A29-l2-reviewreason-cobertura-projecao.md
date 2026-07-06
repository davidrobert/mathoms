---
id: A29.l2
type: lane
title: "cobertura ReviewReason completa em E3 + document_id real + projeção validation_issues (ADR-272 crit. 6)"
sprint: A29
plan: null
status: shipped
ship_pr: 802
ship_date: "2026-07-06"
priority: P1
branch_slug: review-ux-inbox
adrs: ["[[ADR-308]]"]
depends_on: ["[[A29.l1]]"]
tags:
  - type/lane
  - sprint/a29
  - status/shipped
  - priority/p1
  - area/pipeline
---

# A29.l2 — `reviewreason-cobertura-projecao` (pipeline/backend · fecha débito ADR-272 crit. 6)

## Problema

Só 2 de 6 famílias de warning do E3 projetam `ReviewReason`
(`EmptyInstitutionWarning`, `PeriodDerivationWarning`); saldo gap, temporal
gap, anacrônico e divergência de baseline ficam invisíveis à fila.
`_project_reasons` hardcoda `document_id=None` — a UI nunca consegue linkar o
documento. E `StageReview.validation_issues` fica null para E3 (critério 6 da
[[ADR-272]] aberto), jogando a tela no fallback de strings.

## Escopo

1. **`to_review_reason()` nas 4 famílias faltantes** (`SaldoGapWarning`,
   `TemporalGapWarning`, `AnachronicTransactionWarning`,
   `BaselineDiffWarning`) com codes novos na família `domain.*`:
   `domain.balance_gap`, `domain.temporal_gap`,
   `domain.anachronic_transaction`, `domain.baseline_divergence`
   (não `e3.*` — `stage` já é coluna; [[ADR-308]] §4). Mascaramento de
   valores monetários em `offending_value` obrigatório.
2. **`document_id` real** propagado do artefato E2 em
   `e3_reconciler_adapter._project_reasons`; contrato
   `context.document_ref = {document_id, artifact_key}` ([[ADR-308]] §5).
3. **Projeção `ReviewReason → validation_issues`** em
   `_record_stage_needs_review` quando `validation.issues` vem vazio: cap
   top-20 por code (severidade, depois `occurrence_count` desc) + sentinela
   `{truncated: true, remaining: X}` ([[ADR-308]] §3).
4. **`review_reason.schema.json`** bump 1.0 → 1.1 (codes novos, não-breaking).
5. **Copy entries** em `validation-copy.ts` para os 6 codes (microcopy da spec
   do product-designer; título + descrição + consequência).

## Critério de aceite

- `dev/check_needs_review_has_reason.py` verde com as 6 famílias.
- Teste de paridade `review_reasons` ↔ `validation_issues` (mesma fonte,
  ADR-272 crit. 6) para E3.
- Teste de mascaramento: `SaldoGapWarning`/`BaselineDiffWarning` com Money
  sintético não vazam valor em `offending_value`.
- Fixture 100+ docs → `validation_issues` ≤ 20/code + sentinela.
- `test_e3_golden_execution.py` + invariantes de conservação verdes (zero
  rebaseline esperado; se golden capturar `result.detail`, rebaseline via
  manifesto `dev/golden_diff.py` com diff explicado).
- `make update-openapi-snapshot` sem diff estrutural.
- PR mergeado em `main` com CI verde.
