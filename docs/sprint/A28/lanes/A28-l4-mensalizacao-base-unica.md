---
id: A28.l4
type: lane
title: "base de mensalização única: política de janela temporal por família de métrica + Cerbasi coerente"
sprint: A28
plan: PLAN-report-trust
status: shipped
ship_pr: 756
ship_date: "2026-07-03"
priority: P0
branch_slug: mensalizacao-base-unica
adrs:
  - "[[ADR-306]]"
depends_on: []
parallel_with:
  - "[[A28.l2]]"
  - "[[A28.l3]]"
tags:
  - type/lane
  - sprint/a28
  - status/shipped
  - priority/p0
  - area/e5
---

# A28.l4 — `mensalizacao-base-unica` (Onda 0 · Must · **upstream de l1**)

## Problema

Duas bases de mensalização convivem no mesmo relatório sem rótulo, com valores
**2× diferentes**: o headline usa média full-period de 40 meses (receita
66,9k/mês, despesa 44,2k/mês) — **diluída por meses de 2023-24 com cobertura
documental parcial** — enquanto `janela_12m` mostra 113,2k/81,4k. Consequências
em cascata no dogfood `72883bde`:

- A reserva de emergência dimensiona por 44,2k/mês (base diluída) → cobertura
  superestimada.
- A cobertura Perini (renda passiva / despesa mensal) oscila de ~61% para ~33%
  conforme a base — a métrica-âncora da metodologia muda 2× sem explicação.
- `consumo_consciente.folga_mensal` (90,1k) não bate com nenhuma das duas bases.
- O Cerbasi classifica "Gastador" (97,5% presente / 2,5% futuro) **no mesmo
  relatório que celebra 28% de poupança** — `acumuladores_pct_gerador=0` mostra
  que aportes não são reconhecidos como "futuro". Mesmo defeito-raiz: base
  temporal + classificação presente/futuro.

Hoje [FORMULAS.md](../../../reference/FORMULAS.md) tem regra de janela
**fragmentada** (reserva = média trimestral do custo essencial; ratios =
janela_12m; headline = média full-period) — três bases sem decisão canônica.

## Escopo

1. **T0 — ADR `Proposto` de política de base temporal** (obrigatória antes do
   PR de implementação; co-design `financial-planner` + `senior-cto`):
   qual base é canônica por família de métrica (proposta inicial: **janela 12m**
   para ratios/KPIs/reserva/Perini; média full-period **apenas** com rótulo
   explícito de janela) e como meses de cobertura documental parcial entram no
   denominador (excluir mês sem cobertura mínima vs ponderar).
2. Implementar a política no E5: cada métrica mensalizada carrega **rótulo de
   janela no payload** (`janela: "12m" | "40m" | ...`) — a UI nunca mostra duas
   mensalizações sem rótulo (par com [[A28.l9]]).
3. Cerbasi presente/futuro: reconhecer aportes/acumulação como "futuro"
   (`acumuladores_pct_gerador`), recalcular `equilibrio_cerbasi` — rótulo
   coerente com a taxa de poupança exibida.
4. Reconciliar `consumo_consciente.folga_mensal` com a base canônica.
5. Golden re-snapshot **único e explicado** — esta lane fecha ANTES de
   [[A28.l1]] re-snapshotar (evita duplo rebaseline).

## Critério de aceite

- ADR `Proposto` mergeada definindo base canônica por família de métrica;
  flippa `Decidido (A28)` no merge da implementação.
- Toda métrica mensalizada do payload E5 carrega rótulo de janela; teste de
  invariante "nenhum campo `*_mensal*` sem rótulo de janela".
- Cerbasi coerente: fixture dogfood com 28% de poupança **não** classifica
  "Gastador"; `acumuladores_pct_gerador` > 0 quando há aportes no período.
- Cobertura Perini com base declarada e única; `folga_mensal` derivável da
  mesma base (teste de reconciliação).
- Golden re-snapshot com diff explicado; `tests/test_e5_conservation_invariants.py`
  verde.

## Notas

- **Upstream de [[A28.l1]]:** a base mensal decidida aqui é o denominador da
  reserva. Sequência obrigatória l4 → l1 dentro da Onda 0.
- Paralela com [[A28.l2]] e [[A28.l3]] (não compartilham campos).

## Owner

Agente da lane; co-design `financial-planner` (base correta por metodologia) +
`senior-cto` (política/ADR) no T0.
