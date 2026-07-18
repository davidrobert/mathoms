---
id: ADR-333
type: adr
title: "Aporte de investimento é transferência patrimonial, não consumo (taxa de poupança)"
status: Decidido
phase: dogfood cluster C1
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

> Item **C1** do plano PLAN-dogfood-report-fix (achado FIN-01). Implementado
> 2026-07-14 (co-design FP + data-engineer). **Sem bump de `score_version`** — a taxa
> é INPUT do score, não a fórmula (ver Decisão). A batelada `score_version 2.0` de
> C5/FIN-05 ([[ADR-328]]) é mudança de fórmula, separada e futura.

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
  **NÃO alterado neste PR** — usa o modelo 50-15-35 próprio do `equilibrio_cerbasi`
  (`despesa_janela` + `_split_gastos`), independente de `janela_12m.despesa_consumo`;
  permanece como está (sem regressão). **Follow-up:** coordenar o aporte como "futuro
  exatamente uma vez" (residual vs `_split_gastos`) para o card de equilíbrio não
  divergir da taxa de poupança.

**Sem bump de `score_version`.** A taxa de poupança é **INPUT** do componente do score,
não a fórmula (pesos/composição). Por [[ADR-217]] §D3, o bump só ocorre quando a fórmula
muda; aqui o valor do componente sobe (input melhor) e `score_version` segue `1.0-legacy`.
Goldens de score re-baselinam só onde a fixture exercita `aporte_investimento` (sintéticas
sem aporte não mudam).

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
- [[ADR-090]]: campos novos são **Decimal** (padrão `despesa_mensal_essencial` na mesma
  dataclass), serializados como float no `to_dict`; `despesa_consumo` = subtração de dois
  totais já arredondados (exato em cents). Gate `check_float_money` passa (sem float-money novo).
- Schema `e5_analysis` (permissivo; `janela_12m` sem `properties`) aceita os campos aditivos
  sem quebra.
- `score_version` **inalterado** (`1.0-legacy`); só o valor do componente de poupança sobe.

## Critério de aceite (4 lentes)

- **Completude:** `Janela12m` expõe `despesa_consumo` + `transferencia_patrimonial`;
  card, ratio, score e `equilibrio_cerbasi` consomem `despesa_consumo`; CV4 lê `janela_12m`.
- **Corretude:** taxa de poupança recomputada com `despesa_consumo` bate com a
  reportada (diff ≤ threshold); componente do score sobe de ~2,8/10.
- **Consistência:** testes do enricher (`test_fluxo_caixa_enricher.py::TestAporteTransferencia`)
  travam `despesa_consumo == despesa_total − transferencia_patrimonial`,
  `transferencia_patrimonial == Σ despesas_por_categoria[transfer_set]` e `fluxo_liquido`
  inalterado. Witnesses de conservação existentes (`fluxo_liquido`, `Σ por_categoria`) verdes.
- **Precisão:** CV4 vira espelho de `ratios.taxa_poupanca_recorrente_pct` (janela 12m +
  despesa_consumo); `score_version` inalterado (mudança de input); campos novos em `Decimal`.
