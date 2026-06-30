---
id: MOC-sprint-a25
type: moc
title: "Sprint A25 — Data Lineage: reverso + produto N1/N2 + debug LLM"
aliases: ["A25", "Sprint A25"]
sprint_status: done
date: "2026-06-10"
theme: "data-lineage"
---

# Sprint A25 — Data Lineage: reverso + produto N1/N2 + debug LLM

> **Status:** `done` (encerrada 2026-06-16) — promovida em 2026-06-10, sucedendo
> [[MOC-sprint-a24]]. **7/7 lanes shipped**: l1/l3/l4/l5 + cutover do flip dedup v2 e
> `member_hashes` reais (l2/l6, #648) + decisão do `evidencia_path` (l7 — **carry-over
> A26**, requisito de done cumprido). Sem nova `current` promovida (decisão do owner
> 2026-06-16). Fast-follow do plano [[PLAN-data-lineage]]: a A25 **colheu o valor** do
> substrato — query reversa, 1ª UI cliente do lineage e o agente de debug LLM.
> Perfil DIFERENTE da A24: pouco risco de número (lineage é aditivo), muito risco de
> UI/UX (F6) e de eval LLM (F7 define KR1/KR3).
>
> **Carry-overs para A26:** flip `warn→strict` do `evidencia_path` (l7 §Decisão —
> gate idêntico, foco conformidade de path) + drop do shim v1 do dedup (M2, [[ADR-287]]).
>
> **Plano dono:** [[PLAN-data-lineage]] ([plan/DATA_LINEAGE/_README.md](../../plan/DATA_LINEAGE/_README.md)).
> **Prompt de orquestração:** [agent_prompts/orchestrator_a25_f5f6f7.md](../../agent_prompts/orchestrator_a25_f5f6f7.md)
> (pré-revisado PM+CTO 2026-06-10).

## Escopo

- **F5 — lineage reverso** ([[A25.l3]]): `artifact_lineage_edge` + hook pós-run +
  query "números que dependem da fonte X"; retenção N=1 (B6).
- **F6 — produto N1/N2** ([[A25.l5]]): selo `<MonetaryValue/>` + popover "Como
  chegamos a esse número" (4 verbos 1ª pessoa); régua COPY_GUIDELINES §6.3; visual
  snapshot só aqui (G-h).
- **F7 — debug LLM + eval** ([[A25.l4]]): renderer linearizado, `lineage_diff`,
  tools, eval de injeção (KR1 ≥85%, KR3 p95 ≤6; nightly G-g).
- **Herdados:** cutover override v2 ([[A25.l1]], slice 4 da [[A23.l4]]) → flip dedup
  E4→v2 ([[A25.l2]], [[ADR-287]] `Decidido`) → KR2 6/6 ([[A25.l6]], stretch) + decisão
  flip strict `evidencia_path` ([[A25.l7]], requisito de done).

## Lanes (kickoff 2026-06-10 — co-design registrado em cada lane)

| Lane | Slug | Status | Dep |
|---|---|---|---|
| [[A25.l1]] | `a23l4-cutover-override` (dual-read 6 call-sites + flag; M2 → carry-over) | ✅ shipped #604 | A23.l4 s3 ✅ #563 |
| [[A25.l2]] | `dedup-e4-flip-v2` ([[ADR-287]] `Decidido`; slice 1 #619/#621 + **cutover impl. (PR #648)** — resolver+sentinela, flip DEFAULTS→True, rebaseline vazio v2≡v1, G-f zero delta) | ✅ shipped #648 | l1 ✅ |
| [[A25.l3]] | `dl-f5-reverso` (edge table + hook pós-run; teto run→doc documentado) | ✅ shipped #600 | — |
| [[A25.l4]] | `dl-f7-debug-llm` (renderer/diff/tools/eval nightly + seed #606/#607) | ✅ shipped #603 | — |
| [[A25.l5]] | `dl-f6-produto-n1n2` (selo+popover; teste 5s dogfood pendente, flag off) | ✅ shipped #602 | — |
| [[A25.l6]] | `kr2-resto` (parte A ✅ #609 — **KR2 6/6 lineage**; **parte B `member_hashes` reais impl. (PR #648)** — natural_key no item E4 + gate classe-c + fixture K4) | ✅ shipped #609/#648 | parte B: l2 |
| [[A25.l7]] | `evidencia-strict-decision` (ÚLTIMA — **decisão registrada 2026-06-16: carry-over A26** — só 3 gerações c/ telemetria << 20; taxa ~89%, 81% conformidade de path) | ✅ shipped #649 | telemetria |

**Precedência de corte (squeeze):** F7 > F6. MLP = l3+l4+l5 + decisão l7;
l1 must-condicional; l2 must-se-l1; l6 stretch cortável.

## KRs da janela

- **KR1** `localization_accuracy@node ≥ 85%` (nasce em F7; regressão >2pp bloqueia área).
- **KR3** `tool_iterations_p95 ≤ 6`; trace inline ≤1.5k tokens.
- **KR2 6/6** (stretch, via l6) — lista canônica dos 6 registrada no plano §KRs
  (kickoff 2026-06-10): patrimônio (liquido+bruto = 1), reserva, despesa_total,
  investimentos.total, fluxo_liquido, endividamento.total_dividas.
- **Requisito de done:** decisão registrada do flip `warn→strict` do
  `evidencia_path` (flip OU carry-over A26 com gate idêntico). ✅ **Cumprido**
  ([[A25.l7]] §Decisão 2026-06-16): **carry-over A26** — amostra 3 << 20; modo
  segue `warn`. Flip vira lane própria na A26.
