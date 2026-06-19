---
id: A26.l2
type: lane
title: "Flip evidencia_path warn→strict (gate de segurança binário + budget de needs_review)"
sprint: A26
plan: PLAN-data-lineage
status: blocked
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
  - status/blocked
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
  priorizar [[A26.l9]] (citação determinística, A27). O eval 1.8.0 (holdout sintético,
  estratificado-difícil) deu 22% — sinal de que o budget pode ficar apertado em tráfego
  real; medir no real antes de cravar.
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

## Owner

Agente da lane; co-design `prompt-engineer`. UX do `needs_review` (copy) → `product-designer`.
