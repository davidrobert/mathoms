---
id: A32.l7
type: lane
title: "gate: re-run dogfood instrumentado + classificação genuíno-vs-falso + triagem do owner"
sprint: A32
plan: null
status: open
ship_pr: null
ship_date: null
priority: P0
branch_slug: a32-l7-gate-rerun-dogfood
adrs: []
depends_on: ["[[A32.l1]]", "[[A32.l2]]", "[[A32.l3]]", "[[A32.l4]]", "[[A32.l5]]", "[[A32.l6]]"]
parallel_with: []
tags:
  - type/lane
  - sprint/a32
  - status/open
  - priority/p0
  - area/pipeline
  - area/dogfood
---

# A32.l7 — `gate-rerun-dogfood` (prova na run real que a tela parou de mentir)

## Problema

Sem re-run medido contra baseline, os KRs da sprint são opinião. O gate
prova, na run real do owner (`d1732edd`), que os falsos positivos
morreram e que o pipeline não se re-envenena.

## Escopo

1. **Re-extração LLM dos 11 stale (decisão Q1 do owner: completa)** —
   após merge de l2 (contrato novo) e l5: script dirigido da l5
   re-extrai os 11 artifacts E2-llm de mai/jun. Se a l5 tiver recuado
   para tombstone-only, purga explícita por key (padrão l1) + re-run
   dispara a re-extração. Custo LLM aceito pelo owner (cap ADR-173 —
   conferir headroom do mês antes de disparar).
2. **Re-run completo** do pipeline no workspace dogfood; snapshot after
   por code, tabela before/after no `_README.md` da sprint.
3. **Classificação item a item** de cada reason remanescente: genuíno
   (dado do owner) vs falso (abrir issue nomeada). Os `temporal_gap`
   remanescentes classificados **1 a 1** (genuíno vs cascata), igual aos
   `balance_gap` — nunca em bloco (risco assumido do KR2: não foram
   investigados a fundo no dossiê).
4. **Segundo re-run consecutivo** provando não-re-envenenamento (KR4) —
   pressupõe l5 (tombstone) mergeada; escopo do KR4 amarrado aos codes
   efetivamente cobertos pelas lanes mergeadas, não a "todos" de forma
   ambígua.
5. **Sessão de triagem do owner** na tela pós-l6 medindo KR3 (natureza /
   ação / confiança, card a card). Cards não compreendidos viram issues
   nomeadas (anti-Goodhart) — registrados mesmo se o threshold ≥90%
   passar.
6. Registro completo no `_README.md` da sprint. Done = doc mergeado em
   `main` (exceção docs-only; a operação de dado não exige PR de
   código).

## Critérios de aceite

1. KR1: 19 errors/warnings de causa-produto → 0 no re-run.
2. KR2: `balance_gap`/`temporal_gap` só genuínos; delta justificado por
   manifesto `golden_diff` valor-a-valor; `temporal_gap` classificados
   individualmente.
3. KR4: segundo re-run sem novos reasons dos codes cobertos.
4. KR3: triagem do owner documentada (≥90% compreensão / 100% distinção
   de natureza); qualquer falso remanescente vira issue nomeada, não
   silêncio.
5. Tabela before/after por code commitada no `_README.md` da sprint.

## Arquivos load-bearing

| Arquivo | Papel |
|---|---|
| `docs/sprint/A32/_README.md` | Baseline (l1) + destino do before/after |
| Script dirigido da [[A32.l5]] | Re-extração dos 11 stale |
| `dev/golden_diff.py` | Manifesto valor-a-valor (KR2) |
| `backend/app/services/internal_ops/pipeline_reset.py` | Reset parcial se necessário |
