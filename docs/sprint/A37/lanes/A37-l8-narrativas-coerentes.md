---
id: A37.l8
type: lane
title: "Narrativas coerentes com os dados: renda de aluguel, alocação v2, IF probabilística"
sprint: A37
status: planned
priority: P2
branch_slug: a37-l8-narrativas-coerentes
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a37
  - status/planned
  - priority/p2
  - area/pipeline
  - area/domain
---

# A37.l8 — `narrativas-coerentes` (FIN-03 + FIN-05 + FIN-08)

> **Co-design `financial-planner` (1 rodada) antes de codar** — os três itens
> exigem escolher a base/fonte canônica, não só trocar template.

## Problema (evidência verificada 2026-07-20 @ c61c1c29)

1. **FIN-03 — duas rendas de aluguel:** `passive_income` usa o valor anual do
   IRPF (base só imóveis geradores → cap rate 3,77%), enquanto a narrativa s4
   anualiza a média de 40 meses de `fluxo_caixa.por_fonte.receita_aluguel`
   sobre a base total de imóveis de investimento → yield 3,4% e renda ~56%
   maior (`scripts/generate_narratives.py:330-346`). Agravante: a série mensal
   de aluguéis **zera nos 2 últimos meses** (possível vacância/venda) e a
   média histórica é anualizada sem sinalização.
2. **FIN-05 — narrativa em taxonomia v1:** o texto do gráfico de alocação lê o
   rollup legado de 4 classes (`generate_narratives.py:571-574`, template em
   `charts_narrator.py:134+`), enquanto a tabela (`derived.comparaveis`) usa a
   taxonomia v2 de 7 classes renormalizada — granularidade e base divergem na
   mesma superfície.
3. **FIN-08 — certeza indevida:** `charts.projecao_3cenarios.conclusion`
   afirma "Meta será atingida em <ano>" (determinístico,
   `charts_narrator.py:227`) enquanto `if_monte_carlo` do mesmo payload dá
   ~41% de probabilidade até a idade-alvo (p50 no ano seguinte). O parecer
   trata certo; o chart vende certeza.

## Escopo

- FIN-03 (decisão de domínio já colhida na revisão do sprint, 2026-07-20):
  canônica = **aluguel recorrente atual** (janela recente estável), com sinal de
  vacância explícito quando os últimos meses zeram, reconciliado ao valor anual
  do IRPF como âncora — **nunca anualizar média que cruza vacância**. Yield:
  escolher **uma** grandeza e rotular — eficiência de capital (todo o aluguel ÷
  base total de imóveis de investimento) ou cap rate operacional (aluguel dos
  locados ÷ valor dos locados); não misturar numerador de uma com denominador
  da outra (estado atual do payload).
- FIN-05: narrador consome a taxonomia v2 (7 classes) e a mesma base do card;
  aposentar as chaves do rollup v1 no texto.
- FIN-08: linguagem probabilística ("cenário central <ano>; ~X% de chance até
  <idade>"), consumindo `if_monte_carlo` que já está no payload.

## Critério de aceite

- Um único valor de renda de aluguel e um único yield (com base declarada)
  entre `real_estate`, `passive_income` e s4 — unit comparando os campos.
- Narrativa de alocação cita as mesmas classes/percentuais da tabela (unit).
- Chart de projeção não contém "será atingida" sem probabilidade (unit de
  template + golden atualizado).
- Testes de regressão dos três comportamentos atuais antes dos fixes.

## Risco

Médio: golden de narrativas muda (esperado); decisão de base errada re-abre o
item — por isso o co-design antecede o código. Objeção persistente →
`senior-cto` fecha.
