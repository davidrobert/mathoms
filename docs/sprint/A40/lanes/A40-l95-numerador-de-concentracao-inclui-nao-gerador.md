---
id: A40.l95
type: lane
title: "Numerador da concentração imobiliária inclui bem que o motor declara não-gerador"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P0
branch_slug: a40-l95-numerador-de-concentracao-inclui-nao-gerador
owner: financial-planner
depends_on: []
adrs:
  - "[[ADR-340]]"
  - "[[ADR-412]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p0
  - area/pipeline
  - area/financial-planning
---

# A40.l95 — `numerador-de-concentracao-inclui-nao-gerador`

> **Origem:** `RR6-02` da rodada unificada **U2** ([[REPORT-REVIEWS-active]] §r6,
> merge `47970706`). Aritmética reproduzida e verificada pelo loop principal.

## O defeito

```
publicado:          imoveis_fisicos_brl / investivel_efetivo             = 50,62%
sem o não-gerador:  (imoveis_fisicos_brl − imoveis_nao_geradores) / …    = 49,08%
kpi_targets.concentracao_imobiliaria: limiar 50,0 · operador '<'
```

`patrimonio.imoveis_nao_geradores` é a nu-propriedade que
`real_estate.excluded_properties[1]` exclui do cálculo de renda com o motivo **literal**
*"não gera caixa nem está disponível para venda livre"*. A subtração fecha exata contra
`real_estate.valor_total_imoveis`.

**O KPI inverte de veredito** ao remover do numerador um ativo que o próprio motor exclui
duas seções antes.

## Raio — o que este único ativo aciona hoje

`pontos_urgentes[1]` · um risco de severidade **Alta** no parecer §S4 ·
`real_estate.alertas[1] concentracao_alta` · KPI vermelho na tabela de métricas ·
`score.componentes[4]` nota 4,0/10 com peso 12,5%.
O alerta `spread_critico` (piso 45%) **sobrevive**; os demais não.

## Confirmação independente

O braço cego da mesma rodada, **sem ver esta análise**, marcou a alavanca
`indeterminado-por-viés`: o disparo tem margem de **0,62 pp** sobre o limiar, e a base
declarada (`carteira_produtiva_fixa`) não reconstrói a partir de nenhum escalar do payload.
Duas rotas independentes no mesmo alvo.

## Leia antes de abrir escopo

[[A40.l80]] §C6 já mediu que os 10 `kpi_targets` **têm** `base` preenchida e ela é
**incoerente**: *"o problema é o vocabulário do campo, não o preenchimento — senão o fix
vira 'preencher o campo'"*. Confira se a l80 já é dona disso.

## Julgamento de domínio a fechar

As três metodologias de referência medem concentração sobre carteira **produtiva** — ativo
sem caixa e sem liquidez não pertence ao numerador de "imóveis **de renda**". Se a intenção
for medir **iliquidez total**, é **outro KPI**, com outro rótulo e outro limiar. Decida qual,
com o `financial-planner` no planejamento.

Agravante de rótulo na mesma peça: a prosa imprime uma contagem de imóveis de investimento
**menor** que a que o numerador soma.

## Critério de aceite

- Numerador e rótulo concordam sobre o que é medido.
- Se o KPI mudar de veredito, as 5 superfícies que ele aciona mudam **juntas**.
- Emenda datada à ADR canônica do limiar, ou ADR nova se o KPI mudar de identidade.
