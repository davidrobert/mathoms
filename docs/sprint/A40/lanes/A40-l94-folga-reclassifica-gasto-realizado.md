---
id: A40.l94
type: lane
title: "Folga mensal reclassifica gasto pontual realizado como sobra recuperável"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P0
branch_slug: a40-l94-folga-reclassifica-gasto-realizado
owner: financial-planner
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p0
  - area/pipeline
  - area/financial-planning
---

# A40.l94 — `folga-reclassifica-gasto-realizado`

> **Origem:** `RR6-01` da rodada unificada **U2** ([[REPORT-REVIEWS-active]] §r6,
> merge `47970706`). Medido pelo braço cego e confirmado ao centavo pelo loop principal.

## O defeito

A identidade fecha ao centavo (resíduo de arredondamento):

```
folga_mensal × 12  ==  poupança 12m + gastos pontuais 12m
```

Os dois percentuais de "quanto sobra" dividem o **mesmo** denominador
(`fluxo_caixa.janela_12m.receita_recorrente` == `equilibrio_cerbasi.componentes.base`)
e divergem em **19,4 pp** — e a diferença é exatamente `total_pontuais_janela`. Gasto
pontual **realizado** está sendo reclassificado como folga recuperável. A soma fecha dos
dois lados, então nenhuma conservação vê.

**Alcança o usuário:** quem dimensiona aporte pela folga dimensiona **27% acima** do que
a poupança medida sustenta. E a maior das duas sobras é a que **prescreve**.

Irmão na mesma superfície: `equivalente_meses_aporte` mede o estoque de pontuais contra o
aporte **declarado**, não contra a poupança realizada ⇒ fator de inflação **4,9×**.

## §Sequência — leia antes de escolher o fix

O `LC6-05` ([[LEDGER-CERTIFY-active]] §r6) mediu que a base de `total_pontuais`
**inclui aporte e transferência interna**. Consertar a folga sem consertar a base move o
número para **outro valor errado**. O separador de transferência patrimonial **existe** e
é aplicado à janela 12m — não é aplicado à janela que produz `total_pontuais`. Uma
aplicação, dois pontos.

**Não encodei isto como `depends_on`** porque a dependência é de **ordem do fix**, não de
início do trabalho: medir e desenhar pode começar já. Quem executar decide a ordem e a
declara no PR.

## Critério de aceite

- Invariante `|folga_mensal − taxa_poupança × receita_recorrente| ≤ ε` implementado como
  gate, **com prova de que ele reprova com o defeito presente** — gate que nasce verde não
  conta.
- Uma só definição de "quanto sobra" na superfície, ou duas com rótulo de base explícito.
- `equivalente_meses_aporte` declara contra qual grandeza mede.

## Já registrado — marque `MEDIÇÃO-DE-CONHECIDO`

`PV9-13` (a divergência de ~19pp já fora vista no U1; o novo é a identidade exata) ·
`PV9-11` (separador de transferência inerte) · `PV9-12` (moeda como despesa e ativo).

## Re-medição

Cru com valores (off-git): `storage/<ws>/reviews/U2-2026-08-29/SINTESE.md` §"A identidade
sum-preserving que alcançou o usuário".
