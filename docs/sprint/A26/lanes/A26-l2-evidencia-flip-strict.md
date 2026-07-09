---
id: A26.l2
type: lane
title: "Flip evidencia_path warn→strict (gate de segurança binário + budget de needs_review)"
sprint: A26
plan: PLAN-data-lineage
status: in_progress
priority: P1
branch_slug: evidencia-flip-strict
adrs:
  - "[[ADR-279]]"
depends_on:
  - "[[A26.l1]]"
parallel_with: []
tags:
  - type/lane
  - sprint/a26
  - status/in-progress
  - priority/p1
  - area/data-lineage
  - area/llm
---

# A26.l2 — `evidencia-flip-strict` (Regime B · gated por volume)

> **Plano:** [[PLAN-data-lineage]] · executa o flip que a [[A25.l7]] adiou (carry-over).
> **Bloqueada por [[A26.l1]]** (prompt corrigido) **e por volume de produção**. Co-design
> `prompt-engineer` 2026-06-16.

## Objetivo

Virar `evidencia_verification_mode: warn → strict` em `config/prompts/parecer_planejador.yaml`.
Em `strict`, citação que resolve errado dispara o **enforcement per-item** ([[A26.l8]]/
[[ADR-295]]): o item ofensor é descartado (severidade baixa/média) ou o parecer vai a
`needs_review` (severidade alta) — **nunca publica número errado**. É o núcleo do
guardrail anti-alucinação do Parecer.

## Gate (REDEFINIDO 2026-06-19 — separa segurança de UX)

> **Reabre a decisão "gate PER-PARECER <5%"** do orchestrator §5 (marcada "não reabrir"),
> com a mesma força que a [[ADR-295]] reabriu "per-parecer→per-item": **evidência empírica
> nova**. O eval 1.8.0 ([[A26.l8]], strict) mediu `needs_review` per-parecer = **22% (UB
> 35%)** — inatingível abaixo de 5% porque ~87% das falhas é `wrong_pairing` (número real,
> path errado) e ~73% cai em itens severidade alta. O gate <5% **mistura segurança com UX**;
> separe-as.

- **Gate de SEGURANÇA (binário, BLOQUEIA o flip):** **zero citação INCORRETA publicada.**
  Garantido **por construção** pelo enforcement per-item ([[A26.l8]]): no strict, citação
  que resolve errado vira `item_dropped` ou `needs_review`, jamais um número errado no
  output publicado. **✅ já satisfeito** — é o que torna o flip seguro independente da
  taxa de needs_review.
- **Budget de UX (orçamento, NÃO-binário):** taxa de `needs_review` per-parecer **≤15%**
  sobre **≥20 gerações reais** (teto inicial, re-ancorável no 1º tráfego — Regime B).
  Cruzar o budget **NÃO reabre o flip** (a segurança já está garantida); vira sinal para
  priorizar [[A26.l9]] (citação determinística, A27). **Re-eval no 1.9.0** (regra de
  pareamento, 2026-06-19) deu needs_review **6% (ponto) / UB 16,2%** no holdout sintético
  — **sinal favorável** de que o flip passa o budget (vs 22% no 1.8.0); medir no real
  (≥20 ger) antes de cravar, pois UB de n=50 é largo.
- **Query de referência:** `count(*) WHERE evidencia_failed > 0` separado de
  `count(*) WHERE needs_review_triggered` — segurança (zero errado publicado, derivado do
  enforcement) vs. UX (taxa de needs_review).

## Escopo

- 1 linha: `evidencia_verification_mode: strict`. PR com a análise no corpo (segurança
  binária já verde via enforcement + medição do budget de needs_review).
- `needs_review` **é** o fallback graceful ([[ADR-081]]) — sem retry, sem degradação parcial.
- Atualizar `test_parecer_evidencia_path.py` se algum caso default mudar de caminho (o
  enforcement per-item já tem cobertura na [[A26.l8]]).

## Critério de aceite

- **Gate de segurança verde** (zero citação incorreta publicada) — satisfeito por
  construção pelo enforcement per-item ([[A26.l8]]); confirmar no PR.
- **Budget de UX medido** sobre ≥20 gerações reais; se ≤15% → flip; se exceder → flip
  ainda é seguro, mas registrar e priorizar [[A26.l9]] (não bloqueia indefinidamente).
- Baseline de `needs_review` pré-flip registrado. Sem ADR nova (conforma [[ADR-279]] §E +
  [[ADR-295]]; a redefinição do gate é decisão de produto registrada aqui + no orchestrator §5).
- Flip mergeado em `strict` somente após a medição do budget em tráfego real (Regime B);
  pré-launch permanece `blocked` por volume, agora contra um bar atingível.

## Baseline pré-flip — eval sintético 2026-07-01 (holdout PII-zero)

Rodado via [`dev/run_parecer_eval_parallel.py`](../../../../dev/run_parecer_eval_parallel.py)
sobre o holdout estratificado (`tests/fixtures/parecer_eval.py`, n=24 fixtures × 5 runs @
temp 0,1 = 120 gerações + 24 diag @ temp 0). **GATE PASSOU.**

| Métrica | Valor | Nota |
|---|---|---|
| gerações ok | 120/120 | zero erro de LLM |
| **per-parecer violações** | **0** | segurança binária: nenhuma citação incorreta publicada |
| **per-parecer UB IC95** | **3,10%** | budget de UX << teto 15% (era 22% no eval 1.8.0) |
| conformidade de citação | 100,00% | todo `evidencia_path` resolve certo |
| missing_path (pareceres) | 0 | — |
| densidade de âncoras (mediana) | 12,0 | piso `_DENSITY_FLOOR` = 5 |
| R$ na prosa (mediana / total) | 0 / 61 | contrato "LLM não digita R$ na prosa" (mediana 0) |
| diag temp=0 violações | 0 | determinismo sadio |
| custo total | US$ 26,06 | cap US$ 50 |

**Leitura:** o gate de segurança (0 citação incorreta) está verde e o budget de UX
(UB IC95 3,10%) fica muito abaixo do teto de 15% — **sinal fortíssimo de que o flip
strict passa**. **Ressalva:** é holdout **sintético**; o critério de aceite exige repetir
a medição sobre **≥20 gerações reais** (Regime B / tráfego de produção) antes de cravar o
flip. Este baseline remove o bloqueio do lado-eval; resta a confirmação em tráfego real.
Relatório completo (efêmero, gitignored): `_scratch/parecer_eval_report_20260701.json`.

## Estado 2026-07-08 — flip JÁ MERGEADO; resta completar a medição real

- **O flip `warn → strict` está em `main` desde 2026-07-03** — PR
  [#746](https://github.com/davidrobert/mathoms/pull/746) (`0eb76675`). O corpo
  do PR pedia segurar o merge até a medição real; o merge ocorreu antes de ela
  fechar. **Não reverter:** o gate de segurança (zero citação incorreta
  publicada) é satisfeito por construção ([[ADR-295]]) e o budget de UX medido
  no tráfego real ATÉ AGORA está em **0% de `needs_review`** — o flip virou a
  própria medição em curso.
- **Medição real parcial (query em `llm_call_log`): 6/20 gerações sob strict
  (2026-07-03 → 2026-07-08, prompt 2.1.0), `sum(needs_review) = 0`.** Muito
  abaixo do teto de 15%; consistente com o baseline sintético (UB IC95 3,10%).
- **Query de medição** (fechar a lane quando n ≥ 20):
  `SELECT count(*), sum(needs_review) FROM llm_call_log WHERE
  stage='review_finances_holistic' AND created_at >= '2026-07-03';`
- **Critério de fechamento restante:** n ≥ 20 gerações reais com taxa ≤ 15% →
  registrar snapshot aqui + flippar `status: shipped`. Se exceder 15%, o flip
  NÃO reabre (segurança garantida); registrar e seguir — a [[A26.l9]] (já
  entregue, #687) era a mitigação prevista.

## Owner

Agente da lane; co-design `prompt-engineer`. UX do `needs_review` (copy) → `product-designer`.
