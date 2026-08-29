---
id: A40.l92
type: lane
title: "A trilha de progresso ignora a polaridade do operador e enche conforme a métrica piora"
sprint: A40
plan: PLAN-deterministic-authority
status: open
priority: P0
branch_slug: a40-l92-polaridade-do-comparador
owner: product-designer
depends_on: []
adrs:
  - "[[ADR-399]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p0
  - area/frontend
  - area/relatorio
---

# A40.l92 — `polaridade-do-comparador`

> **Origem:** painel de fecho da [[A40.l89]] em 2026-08-28 (`financial-planner` +
> `senior-cto`). Condição nomeada para a l89 poder fechar: residual sem lane vira
> inventário órfão, e **este publica falsidade hoje**.

## O fato

`ParecerMetricasTable.tsx` calcula a trilha como `clamp(atual / alvo × 100, 0, 100)`, sem
noção de direção. Para as **4 chaves com operador de teto** (`<` / `<=`) —
`concentracao_imobiliaria`, `taxa_endividamento`, `alocacao_renda_fixa`,
`despesas_nao_categorizadas` — **a barra enche conforme a métrica piora**.

> **Correção de escopo recebida da [[A40.l93]], 2026-08-28 — são 3, não 4.**
> `alocacao_renda_fixa` deixou de publicar alvo: virou órfã por decisão de domínio
> ([[ADR-399]] §Emenda 2026-08-28), porque desvio de alocação é bidirecional e nenhum
> operador escalar o exprime. Sem `target` não há trilha, então a chave sai da lista
> desta lane. **As 3 que ficam são as que importam** — `concentracao_imobiliaria`,
> `taxa_endividamento`, `despesas_nao_categorizadas` —, e o caso medido abaixo é uma
> delas. O diagnóstico da lane (o `operador` não viaja no wire e o front re-deriva por
> regex sobre a string renderizada) **não muda**.

Caso medido: `taxa_endividamento` 45% contra `≤ 20%` ⇒ `extractNumber("≤ 20,0%") = 20` ⇒
`pct = min(100, 225) = 100` ⇒ **trilha 100% cheia sobre uma violação de 25pp**. Barra cheia
é a gramática visual universal de "meta atingida".

## Por que é P0 e por que agora

O defeito é **anterior** à [[A40.l89]], mas ela o **agravou**: antes, a barra visualizava
um alvo autorado pelo LLM; agora visualiza `limiar_canonico` com procedência declarada — o
selo do produto. É o gêmeo desenhado do `"6 meses ≥ 6 meses"` que a l89 consertou por
escrito, e consertar o texto deixando a figura mentindo é incoerente. Num `<table>` a 12px
o gráfico é lido antes dos dígitos.

## O diagnóstico é de CONTRATO, não de CSS

`operador` existe no `KpiTarget` (`<`, `<=`, `>=`) e **não viaja no wire**. O front
re-deriva por `extractNumber` — regex sobre a string renderizada — e a regex
`[^0-9,.-]` **come o glifo**: `"≤ 20,0%"` e `"≥ 20,0%"` são indistinguíveis para ela.

Isso é a mesma classe do defeito que a [[ADR-399]] fecha, um andar acima: **autoridade
determinística perdida na serialização**. Não se conserta com regex melhor.

## Escopo

1. **Mitigação imediata** (pode sair antes do resto): suprimir a trilha quando o operador
   for de teto. Trilha vazia lê "não medimos" — falso-menor; barra cheia lê "atingido" —
   falso-invertido com o selo do produto.
2. O finalize publica a polaridade: `operador` e/ou `progresso_pct` já computado
   server-side. DTO, snapshot OpenAPI e tipo TS acompanham.
3. Read-path **subtrativo** para pareceres congelados sem o campo — a leitura só remove
   afirmação, nunca acrescenta número a documento entregue ([[A40.l89]] §Escopo 3).
4. O front deixa de fazer regex sobre string renderizada.

## Decisão de produto que a lane precisa (não é de engenharia)

O que "progresso" significa contra um **teto**? Encher ao contrário (100% = folga máxima)?
Binário conforme/violado? Faixa com zona de atenção? A resposta muda o campo que o backend
publica — decidir antes de implementar.

## Fora de escopo

- ~~A polaridade das **regras determinísticas de risco** → [[A40.l90]]~~ — **rota morta
  desde 2026-08-29**: a l90 fechou (`shipped`). O trabalho **volta para esta lane**, que é
  a dona do assunto; rota de trabalho futuro aponta para dono vivo, nunca para uma lane só
  porque o tema nasceu lá.
  **O que a l90 deixou pronto como substrato** (#1813/#1814): a polaridade do gatilho
  virou **dado tipado** — `RiskTrigger.operador` com `conforme()`/`rompido()` em
  [`risk_trigger_registry.py`](../../../../pipeline/domain/services/risk_trigger_registry.py),
  e a §Fronteira registra que `<=` e `<` divergem em 50,00 exato para o mesmo conceito.
  **O que falta é exatamente o §Critério desta lane:** esse operador **não chega ao
  front** — o wire ganhou `kpi_key`, não `operador`. Então "a polaridade chega ao front
  como dado, não por parsing da string" segue aberto, agora com o produtor já tipado.
- Não muta E5 ⇒ **não entra na janela de rebaseline** e não zera o contador de 2 re-runs.

## Critério de aceite

- Nenhuma métrica com operador de teto renderiza trilha que cresce com a piora.
- Prova por mutação: `taxa_endividamento` 45% contra `≤ 20%` **não** pode produzir trilha cheia.
- A polaridade chega ao front **como dado**, não por parsing da string renderizada.
- Baseline visual de print rebaselinada com ≥1 linha de teto, **olhada antes de commitar**.
- Concluído = PR mergeado em `main` com CI verde.
