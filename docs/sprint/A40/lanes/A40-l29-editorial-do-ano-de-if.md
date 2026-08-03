---
id: A40.l29
type: lane
title: "Editorial do ano de IF: dois anos concorrentes, eixo em quando em vez de quanto, e a faixa sem componente"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P2
branch_slug: a40-l29-editorial-do-ano-de-if
adrs:
  - "[[ADR-360]]"
  - "[[ADR-237]]"
depends_on: []
parallel_with:
  - "[[A40.l25]]"
  - "[[A40.l28]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p2
  - area/frontend
  - area/product-design
  - area/financial-planning
---

# A40.l29 — `editorial-do-ano-de-if`

> **Residual da `ADR-361` (PR #1162), itens 4, 6 e 7 do §Deferimento** — os três
> que a [[A40.l25]] declarou explicitamente fora de escopo por dependerem de
> brief: *"reduzir o ano publicado a faixa quando ele existe é decisão editorial
> de S7 e depende de `product-designer` — não abre aqui sem brief"*.
>
> **O primeiro passo desta lane é o brief, não código.** Sem ele a lane fica
> parada; com ele, as três faces caem juntas porque são a mesma pergunta — o que
> a S7 responde sobre "quando".
>
> `ADR-361` fica sem wikilink até #1162 mergear.

## Problema

As três faces têm a mesma raiz: **a S7 responde "em que ano" com mais confiança
do que o modelo tem, e em dois lugares que discordam entre si.**

### 1. Dois anos de IF concorrentes na mesma seção

O determinístico ocupa **dois** slots de destaque (`SectionSummary` da S7 e o KPI
"Ano projetado" do `HeroKpiGrid`); o probabilístico ocupa **um** de rodapé (a
conclusão do chart). A precisão falsa está no lugar nobre, a incerteza honesta na
letra miúda. Para o leitor que mostra o relatório ao cônjuge, a pergunta é
"afinal, qual é?".

Já existe achado de review aberto sobre isto — **RV3-14** em
[[REPORT-REVIEWS]] (P2, `procede-aberto`, dono `product-designer` +
`financial-planner`): *prazo de IF impresso como fato com divergência vs
`p50_ano_if` só em `text-xs`*. Esta lane é o destino executável dele.

### 2. O eixo é "quando", e o dado bom é "quanto"

Recomendação do `financial-planner` no co-design da `ADR-361`: a pergunta
canônica de IF é **quanto de renda o patrimônio sustenta**, não em que data. O
patrimônio mediano na idade-meta já é calculado (`caminho_p50`), é
**incondicional por construção** (percentil pontual sobre `n` cheio, logo sempre
existe mesmo quando o ano é censurado) e, convertido pela TRS já publicada, vira
renda passiva mensal.

Isto é o que **torna a censura da `ADR-361` sustentável**: sem ele, plano ruim
perde a data e o produto fica mudo — e alguém reverte a censura em três meses
para "voltar a mostrar alguma coisa".

### 3. A faixa não tem componente

Os anos do MC **não são renderizados hoje** — chegam ao leitor só pela frase do
narrador e pelo parecer. Com a censura da `ADR-361`, o objeto certo deixou de ser
três células independentes e passou a ser um **intervalo de extremo aberto**. O
`product-designer` especificou `IFFaixaAnos` com a tabela de 5 estados e a regra
que fecha o caso: **`—` fica reservado a "não simulamos"**; "simulamos e não
chega" é `após {ano_horizonte}` — a regra zero-vs-ausente da COPY_GUIDELINES
§4.3 transposta de dinheiro para data.

## Escopo

0. **Brief do `product-designer`** (bloqueia o resto): um ano só na seção, qual
   sobrevive, e se o cone passa a carregar marcador de cruzamento + marca de fim
   de horizonte. Insumo pronto: a especificação já produzida no co-design da
   `ADR-361` (5 estados, copy dos 4 casos, regra do `—`, `severity="info"`).
1. Reduzir a **um** ano na S7. O determinístico, se sobreviver, é enunciado como
   aritmética ("no ritmo de R$ X/mês sem variação de mercado, o gap fecha em N
   anos"), não como previsão. Toca `summaries_narrator`, a conclusão de
   `renda_passiva` e o KPI "Ano projetado".
2. Publicar patrimônio mediano na idade-meta → renda passiva pela TRS, no slot
   que hoje é do ano.
3. Componente `IFFaixaAnos` com os 5 estados, `aria-label` que verbaliza o
   extremo aberto, `tabular-nums`, empilhamento em `<md`.

## Critério de aceite

- Em nenhum estado a seção exibe dois anos de meta diferentes; grep de `if_ano`
  em `summaries_narrator`/`charts_narrator`/`S7IndependenciaSection` não retorna
  slot de destaque.
- `—` aparece **exclusivamente** quando o cone não foi simulado; teste de
  componente cobrindo os 5 estados.
- Nenhum texto dentro do `<canvas>` ou da sua legenda contém ano de meta.
- Snapshot visual nos 2 breakpoints × 2 temas; PDF via Playwright renderiza a
  faixa sem depender de hover.
- Verificação renderizada da S7 (§Débito de método desta sprint).
- RV3-14 fecha junto, ou ganha nota dizendo o que sobrou.

## Fora de escopo

- Semântica do percentil (censura, população) — fechada pela `ADR-361` (#1162).
- Faixa de 5 pp na probabilidade e `sigma` por perfil — [[A40.l25]].
- `idade_meta_if` como input e rename de `p10`/`p90` — [[A40.l28]]. **Sequência:**
  se a l28 rodar antes, o brief já trabalha com os rótulos novos; se rodar
  depois, o brief não muda — são disjuntos por camada (contrato vs exibição).
