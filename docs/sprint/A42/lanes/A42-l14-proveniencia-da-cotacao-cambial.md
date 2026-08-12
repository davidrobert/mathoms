---
id: A42.l14
type: lane
title: "Proveniência da cotação cambial: data na tela e fallback que não inventa número"
sprint: A42
status: planned
priority: P1
branch_slug: a42-l14-proveniencia-da-cotacao-cambial
adrs:
  - "[[ADR-359]]"
  - "[[ADR-378]]"
tags:
  - type/lane
  - sprint/a42
  - status/planned
  - priority/p1
  - area/pipeline
  - area/report
---

# A42.l14 — `proveniencia-da-cotacao-cambial`

> **Origem:** investigação do card Exposição Cambial (2026-08-12). Verificado no DB
> de dogfood, não inferido.

## O defeito

`market_rates` tem USD/BRL 5,80 e EUR/BRL 6,35 com `observed_at = 2026-04-27`.
Em 2026-08-12 isso é **106 dias** de defasagem, e **não existe mecanismo de
atualização de câmbio no produto** — o par mais recente veio de um seed de
migration. O relatório converte saldo em moeda estrangeira e exibe o resultado
sem nenhuma indicação de data.

Não é "106 dias": é **sem teto**. Daqui a três anos serão mil dias com a mesma
apresentação confiante.

Pior que a row vencida é o fallback: `e5_analyzer_adapter` cai em constantes
hardcoded 5,80/6,35 quando o par some do DB. Número plausível, zero proveniência,
usado para sempre e por qualquer workspace sem seed. É a classe [[ADR-359]] —
deve falhar alto ou declarar ausência, nunca emitir um número bonito. As
constantes são hoje **numericamente idênticas** às rows do DB, então nenhum teste
distingue os dois caminhos.

## Não flipa o tier deste workspace

Medido: seria preciso **+55% em USD/BRL** (5,80 → ~9,00) para 6,45% cruzar o piso
verde de 10%. Movimento típico em 106 dias é 3-8%. Logo é P1 de confiança, não P0
de número errado — mas o câmbio alimenta a meta `dolarizacao`, e ali o erro vira
**valor de aporte**.

## Passos

1. **Cotação carrega `observed_at` até a tela e o PDF.** Par, valor e data em
   texto no DOM (não `title=`), porque o PDF é o que chega a terceiros.
2. **Fallback para de emitir número.** Sem par em `market_rates`, a posição vira
   ausência declarada em vez de conversão silenciosa por constante. Teste que
   remove todas as rows e assere degradação — hoje ele exibiria 5,80.
3. **Refresh de PTAX.** BCB é público, gratuito, sem key, e já é a convenção
   declarada no docstring de `MarketRate`. Padrão pronto: Celery + TTL do FIPE
   (ADR-239 D7 / A18.l3). Sem refresh, todo workspace degrada em 6 meses.
4. **Escada de defasagem** (rede de segurança, não solução): ≤30 dias normal;
   31-180 `defasado` — mantém tier, mas some prescrição em **valor** derivada de
   câmbio; >180 tier suprimido com razão declarada. Limiares derivados de "este
   input pode mudar o veredito?", não de estética de calendário.

**Não vira `needs_review`.** Esse estado pede que o *usuário* conserte dado que é
dele; aqui quem não buscou a PTAX foi a plataforma. Enquadre pelo mecanismo, sem
acusar o dono — mesma correção que a [[A40.l22]] fez no `tier_gated`.

## Adjacente, mesma família (verificado)

- **Moeda fora de {USD, EUR} é convertida a taxa 1,0.** O branch é
  `if USD / elif EUR / else: valor_brl = saldo`, e a linha ainda é rotulada como
  moeda estrangeira. Uma conta em libra entra valendo o nominal em reais. Este
  workspace **tem** conta Wise no Reino Unido, e `market_rates` tem par GBP/BRL
  — o dado existe e não é usado.
- **`lastro_moeda` não admite GBP** (CHECK aceita `{BRL, USD, EUR, MIXED, OTHER}`),
  enquanto o caixa aceita qualquer moeda do extrato. Assimetria: quem tem fundo
  domiciliado no Reino Unido não consegue declarar o lastro.
- **Duas taxas convivem no mesmo payload** — informe/baseline 31/12 usa PTAX com
  `ptax_status` gravado; caixa de extrato usa a taxa "mais recente" sem gravar
  nada. `CaixaDetalhe` não tem campo para taxa nem data.
