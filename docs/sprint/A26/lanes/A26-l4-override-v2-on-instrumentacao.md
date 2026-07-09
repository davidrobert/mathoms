---
id: A26.l4
type: lane
title: "Override v2 ON no default + instrumentação do gate (v2_match_count + query agendada)"
sprint: A26
plan: PLAN-data-lineage
status: in_progress
priority: P2
branch_slug: override-v2-on-instrumentacao
adrs:
  - "[[ADR-282]]"
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a26
  - status/in-progress
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

## Escopo (revisto pós co-design 2026-07-01 — ver [[ADR-282]] §Emenda)

- **Emissão:** adicionar `v2_match_count` ao `OverrideMatchIndex` (espelho do
  `v1_fallback_count` já existente), incrementado no ramo `via_v2 is not None`; emitir ambos
  no log estruturado (`mathoms.categorization.dualread`) — observabilidade/debug, **não** é a
  fonte de verdade do gate. Counter per-request no dataclass é legítimo sob [[ADR-111]].
- **Shadow-compare (habilita o gate de corretude da l5):** atrás de flag de observação
  `override_dual_read_shadow_compare`, computar v1 **e** v2 no `match` durante a janela e
  contar `divergence_count` quando `via_v2 != via_v1`. Removido antes da GA.
- **Persistência = `AuditLog`, não tabela nova nem parse de log.** Drenar
  `v1_fallback_count`/`v2_match_count`/`divergence_count` ao **fim do reprocesso de E4** (no
  boundary com `Session`, não no `match()` do domínio — ISP) via novo
  `AuditAction.override_v2_dualread_snapshot` (`details` PII-zero). Sem log aggregator no
  stack, "query agendada sobre logs" é irrealizável; gate vira query SQL pontual sobre
  `audit_log`. (Snapshot diário congelado via Celery beat é **opcional** — só se quiser
  evidência datada no `SMOKE_TEST_HUMAN.md`.)
- **Ordem do flip (armadilha do `_preflight`):** NÃO flipar `DEFAULTS` global como 1º ato —
  trava o backfill (`cutover_already_active`). Sequência: backfill por workspace → flip por
  workspace (override individual) → `DEFAULTS["override_natural_key_v2_enabled"]=True` só ao
  final, como formalização.
- Atualizar `SMOKE_TEST_HUMAN.md`: exercitar os 6 call-sites de override (criar/deletar
  override, preview de regra, learning loop) sob flag-ON — PII fora do CI.

## Gate que esta lane habilita

- **Gate da l4 (cobertura):** `sum(v1_fallback)==0 AND sum(v2_match)>=1` na janela ≥1 sprint
  (query sobre `audit_log`). A 2ª cláusula **prova exercício real** do v2 — mata o "zero por
  inatividade". Satisfeito pelo dogfood do owner (overrides nascem v2, reprocessa E4 flag-ON).
- **Gate adicional que esta lane instrumenta para a l5 (corretude):** `sum(divergence_count)==0`.
  O gate de cobertura é **cego** a override grudado na linha errada (o `match` retorna no 1º
  hit v2 sem consultar v1 → `v1_fallback` fica 0 com a correção no lugar errado). Só o
  `divergence_count` do shadow-compare prova que v2 casa a MESMA linha que v1 — pré-requisito
  do drop irreversível da [[A26.l5]] ([[ADR-282]] §Emenda item 3).

## Progresso (2026-07-02)

- **Instrumentação mergeada:** [#711](https://github.com/davidrobert/mathoms/pull/711)
  (`v2_match_count` + shadow-compare `divergence_count` + snapshot em `AuditLog` via
  `AuditAction.override_v2_dualread_snapshot`) e
  [#713](https://github.com/davidrobert/mathoms/pull/713) (wire do dual-read nos
  consumidores E4).
- **Flip do default mergeado (2026-07-02):** `DEFAULTS["override_natural_key_v2_enabled"]
  = True` + testes explicitam a flag (helper pré-cutover no teste de backfill) +
  `SMOKE_TEST_HUMAN.md` §4.9 (6 call-sites sob flag-ON + snapshot do gate). Seguro
  porque o ambiente real tem 0 override legado pendente (12 = 5 reancorados + 7
  órfãos quarentenados, dogfood ADR-282); a sequência anti-`_preflight` fica
  documentada no comentário do DEFAULTS para ambientes com legado pendente.
- **Resta:** janela de observação ≥1 sprint com uso real (dogfood do owner) —
  `v1_fallback == 0` com `v2_match >= 1` via query no `audit_log` (§4.9 A9.5/A9.6).

## Diagnóstico 2026-07-08 — gate estava VERMELHO por órfão no índice (corrigido)

- **Sintoma:** 9 snapshots consecutivos (2026-07-03 → 2026-07-08) com
  `{v1_fallback: 4, v2_match: 0}` — o oposto do gate.
- **Causa-raiz (reproduzida in-vitro no dado real):** nenhum dos 4 índices de
  match filtrava `orphaned_at`. Os 7 overrides **quarentenados** (dogfood
  ADR-282) continuavam no `by_legacy_hash`; 4 deles casavam por hash v1 com as
  transações da learned rule ativa — contando `v1_fallback` e **sticky-bloqueando
  a rule** (1 caso). Quarentena é terminal e INERTE ([[ADR-282]] §5); sem o
  filtro, o drop da Fase E ([[A26.l5]]) removeria esse comportamento
  silenciosamente — o gate fez o trabalho dele.
- **Fix ([#878](https://github.com/davidrobert/mathoms/pull/878)):** filtro `orphaned_at IS NULL` nos 4 caminhos (learning loop preload,
  apply engine, read-path `load_override_index`, rule preview manual index) +
  4 testes de regressão (`backend/tests/test_override_orphan_quarantine_inert.py`).
  Validação in-vitro pós-fix: índice 12→5, `{v1_fallback: 0}`, learned rule
  aplica nas 4 txs (criando overrides rule-source ancorados em v2 → o run
  seguinte produz `v2_match ≥ 1` e satisfaz "exercício real" organicamente).
- **Consequência para o gate:** a janela de observação **reinicia no merge do
  fix** — filtrar a query por `created_at >= <merge>`; os 9 snapshots antigos
  são o registro do falso-vermelho, não contam para nenhum lado.
- **Nota de contrato:** a key persistida em `audit_logs.details` é `divergence`
  (código `OverrideMatchIndex.snapshot()`), não `divergence_count` — queries do
  gate seguem o código (já refletido no runbook da Fase E, PR #873).

## Critério de aceite

- `override_natural_key_v2_enabled = True` em DEFAULTS; `test_feature_flags` atualizado.
- `v2_match_count` instrumentado + emitido no log; query agendada rodando e persistindo.
- ≥1 sprint observado: `v1_fallback == 0` **com** `v2_match >= 1` (snapshot em `SMOKE_TEST_HUMAN.md`).
- Backend suite verde com o flip (espelha a validação do flip dedup da [[A25.l2]]).

## Owner

Agente da lane; co-design `data-engineer` (counter/gate) + `sre-devops` (query agendada/observabilidade).
