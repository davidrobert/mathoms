---
id: ADR-308
type: adr
title: "Remediação de needs_review unificada na fila de documentos; StageReview como gate de orquestração"
status: Decidido
phase: A29
date: "2026-07-06"
relates_to:
  - "[[ADR-097]]"
  - "[[ADR-111]]"
  - "[[ADR-158]]"
  - "[[ADR-165]]"
  - "[[ADR-272]]"
supersedes: ["[[ADR-158]]"]
superseded_by: []
aliases: ["ADR 308", "review inbox", "remediação needs_review"]
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/ux
---

# ADR-308 — Remediação de `needs_review` unificada na fila de documentos; `StageReview` como gate de orquestração

**Status:** Decidido (A29) • **Data:** 2026-07-06 • **Sprint:** A29 (3/3 lanes shipped 2026-07-06: #800 · #802 · #803).
Co-design: `product-manager` + `senior-cto` + `data-engineer` + `product-designer` (2026-07-06).

## Contexto

Dogfood 2026-07-06: run E3 pausou em `needs_review` e a tela
`/pipeline/runs/[runId]/reviews/[reviewId]` (ADR-158) mostrou 18 strings
duplicadas sem referência a documento ("periodo implausivel…" ×7, "extrato sem
banco determinavel…" ×11) ao lado de um dump JSON de 29KB; únicas ações eram
"Aprovar como está" ou editar o JSON num textarea. O owner aprovou às cegas —
anti-padrão que corrói a confiança no output (gate de saída do dogfood).

Três sistemas não conversam:

1. [[ADR-165]] (`ValidationIssue` + copy amigável) cobre E1/E1.5/E2-llm/E1.6;
   **E3 nunca migrou** — cai no fallback de strings.
2. [[ADR-272]] (`ReviewReason` fonte única, 2 projeções) materializa a tabela
   `review_reasons`, mas o **critério 6 (projeção → `StageReview.validation_issues`)
   está aberto** para E3, e apenas 2 de 6 famílias de warning implementam
   `to_review_reason()` (`_project_reasons` ainda hardcoda `document_id=None`).
3. A fila `/documents?filter=needs_review` (A28.l9) já existe como superfície
   de remediação, mas a tela de review não aponta para ela.

## Alternativas consideradas

1. **E3 emite `ValidationIssue` nativo per-document** (onda nova ADR-165).
   Rejeitada: E3 não é stage LLM; seus problemas são warnings de domínio
   (ADR-097 D1) — forçá-los no contrato de schema-conformity viola a fronteira
   que a ADR-272 traçou, cria segundo produtor e cobra rebaseline de goldens
   sem ganho (o dado já existe em `ReviewReason`).
2. **Endpoint separado `GET .../review-reasons` consumido pela tela** ao lado
   de `validation_issues`. Rejeitada para UI de usuário: duas fontes de verdade
   na mesma tela (ADR-272 §Unificação proíbe). Endpoint permanece candidato
   para console interno (`ops.mathoms.ai`).
3. **Projeção `ReviewReason → validation_issues` no boundary do backend +
   remediação na fila de documentos (escolhida).** Cumpre ADR-272 crit. 6;
   pipeline quase intocado; a UI reusa copy table + `summarizeIssues` já
   entregues pela ADR-165.

## Decisão

1. **`StageReview` é gate de orquestração, não lar de remediação de ingestão.**
   Continua bloqueando `resume_run` enquanto `pending`; a tela agrupa
   pendências e **aponta** para a fila de documentos via
   `review_reasons.document_id` — não hospeda select de instituição nem
   reclassificação.
2. **Dois modos de remediação coexistem, por natureza do stage:** editor JSON
   inline (ADR-158) permanece para stages LLM (ex.: E1.6/IRPF, onde editar o
   extraído faz sentido); problemas de **ingestão** (E3) remediam-se no
   documento, na fila `/documents?filter=needs_review`.
3. **Projeção no boundary:** `_record_stage_needs_review` popula
   `StageReview.validation_issues` a partir das mesmas `ReviewReason`
   (cap top-20 por `code`, ordenado por severidade e `occurrence_count`, com
   item-sentinela `truncated: true, remaining: X`). O total exato vive em
   `review_reasons.occurrence_count`; a UI nunca afirma contagem exata acima
   do cap ("50+").
4. **Cobertura completa de `to_review_reason()` em E3:** as 4 famílias
   faltantes ganham projeção com codes na família existente `domain.*`
   (`domain.balance_gap`, `domain.temporal_gap`,
   `domain.anachronic_transaction`, `domain.baseline_divergence`). **Não**
   criar prefixo `e3.*`: `stage` já é coluna; prefixar fragmentaria a
   agregação cross-stage da query-mãe.
5. **`context.document_ref = {document_id, artifact_key}`:** `document_id`
   real propagado do artefato E2 (fix do hardcode `None`); UI linka
   `/documents/<id>` quando presente, degrada para `artifact_key` textual
   não-clicável quando ausente — nunca link quebrado.
6. **Retomada explícita, nunca reativa:** corrigir documento não re-dispara o
   run (batching: N correções = 1 re-run; determinismo do gate; [[ADR-111]]
   sem triggers fora do Celery). `Document` **não conhece** `pipeline_run` —
   a ligação é unidirecional via `review_reasons.document_id`. O ganho de UX
   vem do banner mudando para "Tudo resolvido — retomar agora" com CTA único.
7. **Taxonomia única nas 3 superfícies** (relatório A28.l9 · fila de
   documentos · tela de review): título e consequência de cada tipo de
   pendência saem de source-of-truth único no frontend (extensão de
   `validation-copy.ts`); só o verbo do CTA muda por superfície.
8. **Ação em lote = stepper sequencial pré-preenchido**, nunca aplicação de
   valor único em massa (11 extratos raramente são do mesmo banco); resultado
   parcial sempre explícito (`{updated, skipped, errors}` por item).
9. **Sem backfill** de reviews antigos (`validation_issues` null → fallback
   legacy com dedup client-side; valor expira sozinho).

## Supersedure parcial de ADR-158

A tela de review deixa de ser o destino de remediação para problemas de
ingestão (o editor JSON permanece para stages LLM). ADR-158 continua válida
como registro da mecânica aprovar/editar/retomar; esta ADR redefine **onde** a
correção de documento acontece. Flip para `Decidido` no merge das lanes A29.

## Consequências

- Zero rebaseline de goldens E3 esperado (validação vive em `result.detail`,
  fora do artefato validado por `e3_reconciled.schema.json`) — confirmar
  empiricamente na lane.
- `review_reason.schema.json` bump 1.0 → 1.1 (adição de codes, não-breaking).
- DTO `StageReviewResponse` não muda de shape (campo já existe; OpenAPI
  snapshot sem diff estrutural).
- KR1 (A29): ≥70% dos reviews resolvidos com ação construtiva (editar /
  corrigir / ignorar-com-consequência-visível) vs. aprovação cega — medido
  pelo evento `review_action` criado na lane A29.l1.
