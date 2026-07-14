---
id: ADR-333
type: adr
title: "Aporte de investimento é transferência patrimonial, não consumo (taxa de poupança + score_version 2.0)"
status: Proposto
date: "2026-07-14"
relates_to:
  - "[[ADR-328]]"
  - "[[ADR-090]]"
  - "[[ADR-217]]"
  - "[[ADR-306]]"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/backend
---

# ADR-333 — Aporte = transferência patrimonial, não consumo

> Item **C1** do plano [[PLAN-dogfood-report-fix]] (achado FIN-01). Irmã de
> [[ADR-328]] (mesmo bump `score_version 2.0`); co-batelada com FIN-05
> (diversificação) e FIN-01 (input de poupança do score).

## Contexto

`taxa_poupanca_recorrente` é calculada como `_ratio_pct(rec_recorrente −
desp_bruto, rec_recorrente)` (`fluxo_caixa_enricher.py:431`), onde `desp_bruto`
acumula **todas** as saídas — inclusive `aporte_investimento`. Na revisão
dogfood o aporte representa ~16,3% da despesa da janela 12m, deprimindo a taxa
de poupança para **14,19%**; a taxa real (excluindo o aporte, que é poupança e
não consumo) é ~27–30%. Consumidores herdam o artefato: o componente
`taxa_poupanca` do score lê `ratios.taxa_poupanca_recorrente_pct`
(`financial_score_calculator.py:266`) e pontua **2,8/10** (peso 2,0) —
subavaliado.

`desp_bruto` vem das linhas sentinela `_total`; `despesas_por_categoria` vem das
linhas de categoria (`_accumulate_despesa`, `fluxo_caixa_enricher.py:457-462`) —
fontes distintas, iguais empiricamente (witness `despesa_total == Σ
por_categoria`, `test_e5_conservation_invariants.py:70-73`). O aporte é uma
saída de caixa **real**, mas conservativa: sai do fluxo e **reaparece no
balanço/investimentos** — não pode sumir.

CV4 (`validate_cross.py:181-189`) está **RED hoje** (`passed=false`, diff
13,2pp) por mismatch de **janela**: recomputa com `fluxo.despesa_total`
(full-period) e compara com um ratio calculado sobre a janela 12m — falso-
negativo de janela, não inconsistência real.

## Decisão

`despesa_total` deixa de ser o denominador de consumo. Divide-se em dois campos
irmãos em `Janela12m` (espelho no full-period por paridade dos cards):

- `transferencia_patrimonial` = Σ `despesas_por_categoria[c]` para `c ∈
  transfer_set` (configurável; hoje `{aporte_investimento}`).
- `despesa_consumo` = `despesa_total − transferencia_patrimonial` (subtração de
  totais **já arredondados**, não re-acúmulo por transação).

`taxa_poupanca_recorrente` passa a usar `despesa_consumo`. `despesa_total`
permanece **bruto** (Σ todas as categorias = Σ sentinela `_total`), preservando
`fluxo_liquido == receita − despesa_total` e `despesa_total == Σ por_categoria`
(witnesses existentes intactos — o aporte reaparece no balanço, o fluxo líquido
continua saída-total).

**Consumidores** (declaração de impacto):

- `financial_score_calculator` componente `taxa_poupanca`: **muda via métrica**,
  sem decisão nova — lê `ratios.taxa_poupanca_recorrente_pct`, que agora reflete
  consumo. Deixa de ser artefato → sobe de ~2,8/10.
- `equilibrio_cerbasi.componentes.poupanca` (`equilibrio_cerbasi_analyzer.py:182`):
  **muda** — o residual `max(0, receita_recorrente − despesa_janela)` passa a ler
  `despesa_consumo`, e o `transfer_set` sai de `gasto_presente`
  (`_split_gastos:202-213`). Efeito coordenado no mesmo bump: o aporte conta como
  futuro **exatamente uma vez** (via residual), coerente com o comentário
  canônico `scoring.json:140` ("aporte é futuro"). Sem coordenar, o
  `equilibrio_cerbasi` contradiria a taxa de poupança.

**Bump `score_version 1.0-legacy → 2.0`** (`financial_score_calculator.py:29`),
batelado com [[ADR-328]]/FIN-05/FIN-01 — re-baselina os goldens de score **1×**
(regra anti-thrashing do [[PLAN-dogfood-report-fix]]).

**CV4** (`validate_cross.py:181-189`): passa a ler `fluxo.janela_12m`
(não full-period) — resolve o falso-negativo de janela **imediatamente** — e,
quando C1 aterrissar, lê `despesa_consumo` (não `despesa_total`), virando
**check-espelho** de `ratios.taxa_poupanca_recorrente_pct`. CV4 pode mergear
**independente do sequenciamento de FIN-01**.

## Rationale

Poupança realizada não é consumo: contá-la como despesa incentiva o oposto do
planejamento consagrado ([[ADR-217]]). Manter `despesa_total` bruto (só
adicionar campos derivados) preserva conservação e charts — o split é aditivo,
não destrutivo. O witness não-tautológico amarra o balde às categorias do
chart, impedindo que um rebaseline futuro cimente um `transferencia_patrimonial`
divergente das barras exibidas.

## Alternativas consideradas

- **Redefinir `despesa_total := despesa_consumo`.** Rejeitada: quebra
  `fluxo_liquido == receita − despesa_total` e `despesa_total == Σ por_categoria`
  (witnesses existentes); o fluxo líquido genuinamente é saída-total.
- **Só corrigir a fórmula da taxa, sem campo `transferencia_patrimonial`.**
  Rejeitada: sem o campo explícito não há witness de conservação; a correção
  vira número mágico não auditável.
- **Witness só `despesa_total == despesa_consumo + transferencia`.** Rejeitada
  por tautológica (a definição de `despesa_consumo` a satisfaz por construção);
  exige-se também o laço com as categorias do chart.

## Consequências

- Taxa de poupança sobe ~14,19% → ~27–30%; componente do score deixa de ser
  subavaliado. Card/parecer passam a refletir aporte como poupança.
- [[ADR-090]]: campos novos seguem o padrão `float + round(v,2)` do dataclass
  (`Janela12m.to_dict`); o witness em cents é exato porque cada valor é
  round-to-2 antes de virar cents, e `despesa_consumo` é subtração de dois
  totais já arredondados. **Nenhuma nova violação de float em acumulação.**
- Schema `e5_analysis` (permissivo, sem `version` explícito; `janela_12m` sem
  `properties`) aceita os campos aditivos sem quebra; o gate real é o witness de
  conservação (`mode=warn` default).
- `score_version 2.0` re-baselina goldens de score 1× junto com [[ADR-328]].

## Critério de aceite (4 lentes)

- **Completude:** `Janela12m` expõe `despesa_consumo` + `transferencia_patrimonial`;
  card, ratio, score e `equilibrio_cerbasi` consomem `despesa_consumo`; CV4 lê `janela_12m`.
- **Corretude:** taxa de poupança recomputada com `despesa_consumo` bate com a
  reportada (diff ≤ threshold); componente do score sobe de ~2,8/10.
- **Consistência:** witnesses novos em `test_e5_conservation_invariants.py`
  (cents, tolerância 0): `despesa_total == despesa_consumo +
  transferencia_patrimonial` **e** `transferencia_patrimonial == Σ
  despesas_por_categoria[transfer_set]`; witnesses existentes (`fluxo_liquido`,
  `Σ por_categoria`) permanecem verdes.
- **Precisão:** CV4 vira espelho de `ratios.taxa_poupanca_recorrente_pct`;
  `score_version 2.0` bumpado; goldens re-baselinados 1×.
