---
id: A26.l4
type: lane
title: "Override v2 ON no default + instrumentação do gate (v2_match_count + query agendada)"
sprint: A26
plan: PLAN-data-lineage
status: blocked
priority: P2
branch_slug: override-v2-on-instrumentacao
adrs:
  - "[[ADR-282]]"
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a26
  - status/blocked
  - priority/p2
  - area/data-lineage
  - area/observability
---

# A26.l4 — `override-v2-on-instrumentacao` (Regime B · habilitador do gate da l5)

> **Plano:** [[PLAN-data-lineage]] · pré-requisito da M2 destrutiva do override ([[A26.l5]]).
> Co-design `data-engineer` + `sre-devops` 2026-06-16. Resolve dois **bloqueadores duros**:
> a flag do override está default-OFF e o gate de fallback é hoje **inauditável**.

## Por que existe (achados do co-design)

1. **`override_natural_key_v2_enabled` é default `False` hoje.** O read-path da [[A25.l1]]
   usa v2 *sob flag*, mas com default-OFF o ramo v2 não roda em produção → o counter
   `dualread.v1_fallback` fica zero **por construção** (zero vácuo). Sem flipar e
   exercitar, o gate "counter zerado ≥1 sprint" da [[A26.l5]] é falsamente verde.
2. **O counter é só `logger.info`** (`override_dual_read.log_v1_fallback`, sem métrica
   agregável). Provar "zero por ≥1 sprint" exige grep ad-hoc frágil — gate não-auditável.

## Objetivo

Tornar o gate da M2 override **real e auditável**: ligar o caminho v2 em produção e
instrumentar a verificação.

## Escopo

- Flipar `DEFAULTS["override_natural_key_v2_enabled"] = True` em `feature_flags_service.py`.
  Rollback = flag off por workspace (read-path volta a v1). NÃO é destrutivo.
- Adicionar `v2_match_count` ao `OverrideMatchIndex` (espelho do `v1_fallback_count` já
  existente), incrementado no ramo `via_v2 is not None`; emitir ambos no log estruturado.
- **Query agendada** (cron/scheduled task) que conta `event=v1_fallback` e `v2_match` por
  dia e persiste em registro auditável (tabela `ops_metrics` ou doc append-only commitado).
- Atualizar `SMOKE_TEST_HUMAN.md`: exercitar os 6 call-sites de override (criar/deletar
  override, preview de regra, learning loop) sob flag-ON — PII fora do CI.

## Gate que esta lane habilita (G2 da l5)

`sum(v1_fallback) == 0 AND sum(v2_match) >= 1` na janela de ≥1 sprint. A 2ª cláusula
**prova exercício real** do v2 — mata o "zero por inatividade". Satisfeito pelo dogfood do
owner (overrides nascem v2, reprocessa E4 sob flag-ON).

## Critério de aceite

- `override_natural_key_v2_enabled = True` em DEFAULTS; `test_feature_flags` atualizado.
- `v2_match_count` instrumentado + emitido no log; query agendada rodando e persistindo.
- ≥1 sprint observado: `v1_fallback == 0` **com** `v2_match >= 1` (snapshot em `SMOKE_TEST_HUMAN.md`).
- Backend suite verde com o flip (espelha a validação do flip dedup da [[A25.l2]]).

## Owner

Agente da lane; co-design `data-engineer` (counter/gate) + `sre-devops` (query agendada/observabilidade).
