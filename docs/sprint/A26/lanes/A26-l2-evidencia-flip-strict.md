---
id: A26.l2
type: lane
title: "Flip evidencia_path warn→strict (gate per-parecer <5%)"
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

Virar `evidencia_verification_mode: warn → strict` em `config/prompts/parecer_planejador.yaml`
— uma violação de citação passa a rejeitar o parecer (→ `needs_review`), em vez de só logar.
É o núcleo da consolidação do guardrail anti-alucinação do Parecer.

## Gate (redefinido vs. A25.l7 — **per-parecer**, não per-citação)

A taxa de 89% da [[A25.l7]] era **per-citação** (`failed/(failed+verified)`). Mas em
`strict` **uma** falha → o parecer inteiro vira `needs_review`. Logo o gate de flip deve
medir o que o strict realmente bloqueia:

- **Gate primário (flip):** **% de pareceres com ≥1 violação < 5%** sobre **≥20 gerações**
  reais — OU o eval golden holdout da [[A26.l1]] <5% como proxy documentado (pré-launch),
  com re-validação em produção em 30 dias anotada no PR.
- **Gate secundário (saúde):** taxa-citação <~2% como leading indicator + baseline de
  `needs_review` por geração instrumentado **antes** do flip (transparency backfire).
- **Ajuste da query de referência** (herdada da [[A25.l7]]): adicionar
  `count(*) WHERE evidencia_failed > 0` (pareceres com ≥1 falha), não só somar citações.

## Escopo

- Re-medir pós-[[A26.l1]] com o gate per-parecer (produção ≥20 ger OU eval holdout).
- 1 linha: `evidencia_verification_mode: strict`. PR com a análise no corpo (gate
  per-parecer, banda do eval, holdout).
- `needs_review` **é** o fallback graceful ([[ADR-081]]) — sem retry (não muda outcome
  de citação determinística) e sem degradação parcial (abre buraco de auditoria). Violação
  em strict → `needs_review` direto.
- Atualizar `test_parecer_evidencia_path.py` se algum caso default mudar de caminho.

## Critério de aceite

- Gate primário verde (% pareceres com ≥1 violação <5% sobre ≥20 ger OU eval holdout <5%).
- Baseline de `needs_review` pré-flip registrado; pós-flip não dispara desproporcionalmente.
- Flip mergeado em `strict` **somente** após gate verde; senão **carry-over A27** com gate
  idêntico (não sequestra o fechamento da A26). Sem ADR nova (ADR-279 §E cobre).

## Owner

Agente da lane; co-design `prompt-engineer`. UX do `needs_review` (copy) → `product-designer`.
