---
id: A40.l38
type: lane
title: "Caixa canônico: denylist de instituição suprime R$ 89k do bruto e a conservação não vê"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P0
branch_slug: a40-l38-caixa-canonico-extrato
adrs:
  - "[[ADR-376]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p0
  - area/pipeline
  - area/financial-planning
---

# A40.l38 — `caixa-canonico-extrato`

> **Aberta em 2026-08-11**, derivada da investigação do card "Posição por
> Instituição e Moeda (31/12)" (memória do projeto, run `ee124571`).
> Co-design: `financial-planner` + `senior-cto` + `data-engineer` (2026-08-11).

## Problema

`_load_caixa_from_e3` exclui contas por denylist hardcoded de "bancos de
investimento" ([e5_analyzer_adapter.py:846](../../../../pipeline/domain/services/e5_analyzer_adapter.py)).
Medido no dogfood: **R$ 89.121,80 fora do patrimônio bruto** (PicPay
R$ 53.756,56 + Rico R$ 35.365,24), enquanto BTG entra **por acidente de
string** (`"btg pactual"` ≠ `btgpactual`). O teste do skip usa o mesmo nome
com espaço — teste e código compartilham a crença errada. A suíte inteira
fecha verde com o dinheiro sumido.

## Entregável

PR único (P0):

1. Deleta `_investment_banks`/`_load_investment_banks`; caixa da visão
   corrente = `saldo_final` do último extrato reconciliado por conta, contado
   exatamente 1× ([[ADR-376]] §1-2).
2. Exclusões remanescentes (fatura/poupança/PJ/`saldo_final_unknown`) viram
   razões tipadas observáveis ([[ADR-097]] D1).
3. Gate de conservação exclusiva em `tests/test_e5_conservation_invariants.py`:
   `caixa_total == Σ saldos elegíveis` **e** nenhum banco com extrato elegível
   presente como posição cash-like no E4.
4. Rebaseline (goldens + view-model snapshot) em commit isolado com manifesto
   `dev/golden_diff.py` — causa nominal por linha.
5. Flip da [[ADR-376]] para `Decidido (A40.l38)`.

## Critério de aceite

- Teste determinístico do mecanismo (fixture com banco-de-corretora sem
  posição E4 → saldo entra) **e** medição da instância no dogfood
  (`caixa_total_brl` sobe exatamente R$ 89.121,80 no run de verificação).
- `tests/test_e5_conservation_invariants.py` passa **sem edição** no commit
  de rebaseline.
- Nenhuma conta some do caixa sem razão tipada emitida.
- Suíte pipeline + backend verdes; manifesto de rebaseline no corpo do PR.
