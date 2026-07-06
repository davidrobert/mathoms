---
id: MOC-sprint-a29
type: moc
title: "Sprint A29 — Review UX: conferência de pipeline centrada em documentos"
aliases: ["A29", "Sprint A29"]
sprint_status: current
date: "2026-07-06"
theme: "review-ux-inbox"
---

# Sprint A29 — Review UX: conferência de pipeline centrada em documentos

> **Status:** `current` (promovida 2026-07-06) — sucede [[MOC-sprint-a28]]
> (`done`). Origem: dogfood do owner em 2026-07-06 — run E3 pausou em
> `needs_review` e a tela mostrou 18 strings duplicadas sem documento + JSON
> 29KB; owner aprovou às cegas. Co-design 2026-07-06: `product-manager`
> (fases/gate/KR) + `senior-cto` (arquitetura da projeção, boundary de
> retomada) + `data-engineer` (cobertura ReviewReason, document_ref, caps) +
> `product-designer` (spec v1.5 + inbox). ADR canônica: [[ADR-308]] (Proposto).
>
> **Decisão de escopo:** o gate de medição F0 (abrir F2 só se ≥3 reviews
> E3/run limpo) foi **overridden pelo owner** ("vamos atuar em tudo",
> 2026-07-06) — as 3 lanes executam em sequência. A query de medição
> permanece na l1 como baseline do KR2.

## Tese

O usuário nunca deve revisar "output de stage": ele confere **documentos**
com pendências nomeadas, agrupadas e com consequência explícita. A infra já
existe em ~80% ([[ADR-272]] materializa `ReviewReason`; A28.l9 criou a fila
`/documents?filter=needs_review`) — a sprint conecta as pontas e fecha o
débito ADR-272 crit. 6.

## Lanes (3, sequenciais por dependência de dados)

| Lane | Escopo | Prioridade |
| --- | --- | --- |
| [[A29.l1]] `review-screen-v15` | Tela de review: dedup+agrupamento, hierarquia de ações com consequência, JSON em details, h1 de tarefa, telemetria `review_action` | P0 |
| [[A29.l2]] `reviewreason-cobertura-projecao` | 4 famílias `to_review_reason()` + `document_id` real + projeção `ReviewReason → validation_issues` (cap 20/code) + copy entries | P1 |
| [[A29.l3]] `inbox-pendencias-documents` | Endpoint de pendências agrupadas + `PendingReviewQueue` em `/documents` + banner "análise pausada" + retomada explícita | P1 |

## KRs

- **KR1 — % de reviews resolvidos com ação construtiva** (editar / corrigir /
  ignorar-com-consequência) vs. aprovação cega: baseline 0%, meta ≥70%.
  Instrumentação: evento `review_action` (l1).
- **KR2 — reviews E3 por run limpo** (tendência ↓): query em `review_reasons`
  (já existe, ADR-272); baseline medido na l1 pós-A28.l8.

## Fora de escopo

- Backfill de reviews antigos (fallback legacy cobre; [[ADR-308]] §9).
- Retomada automática do run ao resolver pendências (decidido explícita —
  [[ADR-308]] §6).
- Editor JSON: permanece como está para stages LLM (E1.6); não é tocado.
