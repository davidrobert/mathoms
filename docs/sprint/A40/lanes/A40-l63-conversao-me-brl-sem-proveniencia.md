---
id: A40.l63
type: lane
title: "Conversão ME→BRL não registra proveniência: taxa hardcoded indistinguível de taxa real, e saldo BRL rotulado como USD"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l63-conversao-me-brl-sem-proveniencia
owner: data-engineer
adrs:
  - "[[ADR-090]]"
  - "[[ADR-245]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/pipeline
  - area/money
---

# A40.l63 — `conversao-me-brl-sem-proveniencia`

> Aberta em 2026-08-15 no co-design do P0 nº 2 da [[A40.l50]]
> (`financial-planner` + `senior-cto`). **Nenhum destes achados estava no
> inventário da l50**, e nenhum pertence à [[A40.l39]] — ela resolve a
> superfície da tabela, não a conversão que a alimenta.

## Problema

Três produtores alimentam a mesma coluna de valor convertido, e **nenhum
registra a taxa que usou**. A informação de qual linha veio de onde existe
(`fonte`), mas a taxa não — então nenhum consumidor consegue fazer afirmação
verdadeira sobre a conversão, só afirmação falsa ou silêncio.

### 1 · Taxa hardcoded indistinguível de taxa real

`e5_analyzer_adapter.py:902-910` cai em `5.80` / `6.35` literais quando o
`ConfigStore` não resolve `market_rate`. Nada no payload E5 e nada no log
registra que isso aconteceu — `grep` no `e5_analysis.schema.json` confirma que
**a taxa corrente aplicada não é exposta em lugar nenhum**. Hoje ninguém sabe
com que frequência dispara.

### 2 · Fallback da [[ADR-245]] rotula BRL como USD

`_extract_me_caixa_from_baseline` (`e5_analyzer_adapter.py:1085-1129`) constrói
`CaixaDetalhe` com `saldo_original` **em BRL** e `moeda="USD"` (default
conservador em `:1082`), `fonte` no default `"extrato"`. O card renderiza a
linha secundária como `US$ <valor em BRL>`.

**Latente** — só dispara com `not has_foreign_in_e3` — e por isso **sem
sintoma**: mais grave que o rodapé PTAX que originou a investigação, e sem nada
que o denuncie.

### 3 · A assimetria é do produtor, não da linha

`posicao_31_12_builder.py:97-114` — a row do payload E5 **já tem** os três
campos de PTAX; `_posicao_from_extrato` os preenche com `None` explícito. Quem
não tem o que preencher é `CaixaDetalhe` (`patrimonio_types.py:195-208`), que
carrega `saldo_original`, `valor_brl`, `moeda`, `fonte` e `data_referencia` —
nenhum campo de taxa ou status.

### 4 · A cotação corrente está 106 dias defasada (2026-04-27)

Não é bug de conversão; é a ausência do rótulo que faria isso incomodar quem lê.

## Escopo

1. **Conversor único ME→BRL** devolvendo value object com `valor_brl`, `taxa`,
   `taxa_data`, `taxa_fonte` (enum fechado: `ptax_31_12` |
   `market_rate_corrente` | `default_hardcoded` | `nao_convertido`) e `status`.
   As três vias passam por ele. Fecha a classe **por tipo**, não por regex.
2. Matar o `5.80`/`6.35` hardcoded como valor silencioso — ele vira
   `taxa_fonte="default_hardcoded"` com `WARNING` estruturado e contagem de
   linhas afetadas (sem valor monetário no log).
3. Corrigir o fallback da [[ADR-245]]: `moeda` e `saldo_original` param de se
   contradizer.
4. **Gate.** O funil estrutural é o que fecha a classe — via nova não consegue
   produzir a coluna sem passar pelo conversor, porque o tipo não deixa.
   Backstop barato em pre-commit (multiplicação por `cambio*`/`ptax`/`quote.rate`
   fora do módulo conversor é ofensor) fecha a **sintaxe**, não a classe — não
   confundir os dois. Ratchet por allowlist **nominal** `(módulo, produtor) → WHY`,
   nunca contador de linhas.

## Fora de escopo

- **Qual taxa a coluna "31/12" usa** — é [[ADR-382]] e [[A40.l39]].
- **Matar `CaixaDetalhe.valor_brl: float`** — campo novo nasce `Decimal`, mas
  trocar o legado move centavos publicados e consome re-run por ganho ortogonal.
  Morre na lane de float-money, com `dev/golden_diff.py` e manifesto.

## Critério de aceite

- Golden de execução mostrando as três vias com `taxa_fonte` distinto.
- Caso `default_hardcoded` exercitado com `ConfigStore` sem `market_rate` — hoje
  ninguém sabe quando dispara.
- Regressão do fallback [[ADR-245]] provando que `moeda`/`saldo_original` param
  de se contradizer.
- Prova de mutação: reintroduzir a multiplicação crua num dos três produtores
  derruba o gate.
- Campo novo **não** entra em `required` no schema — leitor histórico é tolerante.

## Pendente de decisão

ADR própria: nenhuma vigente cobre. A [[ADR-090]] decide **representação**
(float vs Decimal), a [[ADR-238]] D5 decide **precedência** entre fontes (e a
[[ADR-382]] D4 já a mata), e a [[ADR-387]] D3 é a mesma classe escopada a
proteção. A nova é "D3 generalizada": *valor monetário derivado de conversão
carrega taxa, data, fonte e status de enum fechado; ausência é status explícito,
nunca `null` silencioso*. Prioridade e onda são gatilho de `product-manager`.
