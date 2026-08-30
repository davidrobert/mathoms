---
id: ADR-422
type: adr
title: "A folga é a poupança da janela, não a poupança mais o gasto pontual realizado"
status: Decidido
phase: A40
date: "2026-08-29"
relates_to:
  - "[[ADR-306]]"
  - "[[ADR-333]]"
  - "[[ADR-090]]"
  - "[[ADR-161]]"
supersedes: []
aliases: ["ADR 422", "folga mensal", "consumo consciente"]
tags:
  - type/adr
  - status/decidido
  - area/e5
  - area/dominio
  - sprint/a40
---

# ADR-422 — A folga é a poupança da janela

**Status:** Decidido (A40.l94 · #1828 `05561dc0`) • **Data:** 2026-08-29 • Co-design
`financial-planner` no **planejamento**. Emenda [[ADR-306]] §D6 no termo de
pontuais; consome a separação de [[ADR-333]].

## Contexto

`consumo_consciente.folga_mensal` era, literalmente:

```
pontual_mensal              = pontuais_janela / n_meses
despesas_recorrentes_mensal = despesa_mensal_media − pontual_mensal
folga_mensal                = receita_rec_mensal − despesas_recorrentes_mensal
teto_sugerido               = despesas_recorrentes_mensal × 1,15
```

que se reduz a **`folga_mensal ≡ poupança_mensal + pontual_mensal`**. O gasto
pontual **realizado** voltava ao numerador como sobra recuperável.

A consequência é que a mesma página publicava **dois** "quanto sobra" sobre o
**mesmo** denominador — `fluxo_caixa.janela_12m.receita_recorrente`, que é
idêntico a `equilibrio_cerbasi.componentes.base` — sem rótulo que os
distinguisse:

| superfície | número | valor no dogfood |
| --- | --- | --- |
| hero (`HeroKpiGrid`) | `ratios.taxa_poupanca_recorrente_pct` | **57,32%** |
| card S2 (`ConsumoConscienteCard`) | `consumo_consciente.folga_pct` | **76,70%** |

19,4 pp de divergência, e a diferença é **exatamente** `total_pontuais_janela`.
A ponte é identidade derivável, não coincidência do corpus:

```
folga_mensal − poupança_mensal ≡ (pontuais_janela − transferencia_patrimonial) / n_meses
```

Verificada em dois payloads: dogfood (`130.179,78 − 97.302,65 = 32.877,13 ==
394.525,39/12`, resíduo de R$ 0,01) e a fixture `pontuais-com-aporte`
(`15.000,00 − 14.250,00 = 750,00 == (21.000 − 12.000)/12`, resíduo zero).

**A soma fecha dos dois lados**, então nenhum invariante de conservação via o
defeito — é a classe *sum-preserving* que a rodada unificada existe para pegar,
e ela alcançou o usuário: **a maior das duas sobras é a que prescreve**
(`teto_sugerido` sai da mesma subtração, e o parecer ancora conselho de
contenção nela). Quem dimensiona aporte pela folga compromete, todo mês, a
provisão inteira dos gastos pontuais — e quebra o aporte no primeiro evento.

Origem: `RR6-01` ([[REPORT-REVIEWS-active]] §r6, rodada U2). Medição-de-conhecido
de `PV9-13`; o que é novo é a identidade fechada ao centavo.

### Por que [[ADR-306]] §D6 não basta

D6 decidiu a fórmula acima e chamou-a de *"folga mensal reconciliável"*. Ela
consertou uma **mistura de base** real (pontuais full-period ÷ denominador 12m) e
**não se pronunciou** sobre duas perguntas distintas: se somar o pontual de volta
é certo, e se a base de pontuais é consumo. A reconciliação que D6 pediu foi
implementada como teste — e o teste reconstruía a fórmula defeituosa, sobre
fixtures com `total_pontuais_janela == 0`: **teste e código compartilhavam a
crença errada, e o termo em disputa nunca era exercitado**.

## Decisão

**D1 — A folga é a poupança da janela.**

```
folga_mensal = receita_recorrente_mensal_12m − despesa_consumo_mensal_12m
```

A base é `despesa_consumo` ([[ADR-333]]), não a despesa bruta: com a bruta, o
aporte da janela reintroduz a divergência por outro termo (`− transferencia/n`),
e a folga pode ficar **abaixo** da poupança. Com D1, o invariante
`|folga_mensal − taxa_poupança × receita_recorrente| ≤ ε` vale **por construção**.

Rejeitada a alternativa "manter os dois com rótulo impresso", que era a
ferramenta certa para o problema errado: rótulo resolve **ambiguidade de
escopo** (foi o que a [[A40.l3]] fez, e funcionou). Aqui os dois números têm a
mesma base temporal e o mesmo denominador — o conflito é de **veredito**, e
rotular dois vereditos incompatíveis publica os dois.

Rejeitada também a variante "só o pontual discricionário volta": `nao_identificado`
é a categoria-lixo default, e ela cairia em "discricionário" — a regra
classificaria como cortável exatamente o que não é consumo (57,5% da janela do
dogfood).

**D2 — `teto_sugerido` sai do contrato.** Três defeitos independentes: (i)
prescrevia R$ 45.519,51 contra despesa real de R$ 72.459,30/mês — 37% abaixo do
que a família gasta, e teto inalcançável é o mecanismo nº 1 de abandono de
orçamento na literatura de referência do domínio; (ii) o rótulo dizia "consumo" e o número era
`recorrente × 1,15`, incluindo moradia, impostos e folha PJ; (iii) o
multiplicador `1,15` não tem origem declarada em lugar nenhum. Rebasá-lo para
consumo produziria `72.459,30 × 1,15 = 83.328,20`, isto é *"gaste até 15% a mais
do que já gasta"* — permissivo a ponto de ser vazio. Um número que só pode ser
inalcançável ou vazio não é teto. Teto de verdade é escopo do
`OrcamentoProspectivoCard`, que já é a superfície de tetos; duplicá-lo repetiria
esta doença.

**D3 — `equivalente_meses_aporte` → `equivalente_meses_poupanca`.**

```
equivalente_meses_poupanca = total_pontuais_janela ÷ folga_mensal
```

O anterior media o estoque **full-period** contra o aporte **declarado**
(`goals.aportes.meta_aporte_mensal`): duas bases, e um denominador **editável
pelo usuário** — um número de diagnóstico que se move sem que nada tenha
acontecido no mundo não é auditável. No dogfood o fator de inflação era **4,9×**
(46,1 meses onde a poupança realizada sustenta 4,1), e o próprio aporte de
R$ 190.000 contava como 9,5 "meses de aporte" dentro do numerador.

Numerador e denominador saem da **mesma** janela — trocar só o denominador
recriaria a mistura de base que a [[ADR-306]] existe para matar. Atribuição do
delta: só denominador = 9,5; só numerador = 19,7; **ambos = 4,1**. A comparação
com a meta declarada pertence ao plano de ação, onde meta é o objeto, não ao card
de diagnóstico.

**D4 — A prosa do E5 declara as duas janelas.** `analise` era a única superfície
que citava um total **nu**.

## Consequências

- `folga_pct == taxa_poupanca_recorrente` por construção. O par deixa de ser dois
  vereditos e passa a ser um, medido em duas unidades.
- **Nenhum consumidor de score muda**: o score já lia
  `ratios.taxa_poupanca_recorrente_pct` — o número **conservador**. Quem lia o
  inflado era o card e o parecer, isto é, as superfícies que **prescrevem**.
- `manifest_version` do parecer sobe (2.7.0 → 2.8.0) e **cobra a frota**: a
  `folga_mensal` mudou de VALOR sem mudar de nome, e o cache tem TTL de 7 dias.
- No dogfood: folga R$ 130.179,78 → R$ 97.302,65; `folga_pct` 76,70 → 57,32;
  equivalente 46,1 → 4,1 meses.

### O que esta ADR NÃO conserta — e por que isso não muda o sinal

A base de `total_pontuais` continua contaminada (`LC6-05`): no dogfood, 57,5% da
janela é movimentação patrimonial — uma saída de R$ 194.886,65 nomeando outro
banco do próprio titular e R$ 32.000 em conversões BRL→USD, todas caídas em
`nao_identificado` porque o `InternalTransferDetector` não as pegou. Há **três**
definições disjuntas de "gasto pontual" em produção:

| produtor | exclui |
| --- | --- |
| `FluxoEnricherConfig.transfer_categories` ([[ADR-333]]) | `aporte_investimento` |
| `consumo_pontuais.py::_is_pontual` (a **lista** do card) | transferência interna detectada + 3 categorias |
| `ConsumoConscienteCalculator._collect_candidates` (o **KPI**) | nenhum dos dois |

Sob a fórmula anterior essa contaminação era **fatal**, porque entrava na prescrição
**determinística**. Sob D1 ela não alcança mais folga nem teto — o teto não existe mais.
Por isso a ordem é esta e não a inversa, e por isso o conserto da base é lane própria, com
delta atribuível a uma causa só.

> **Precisão 2026-08-30 (closeout).** Uma versão anterior deste parágrafo dizia que a
> contaminação passa a degradar *"apenas números descritivos"*. É largo demais: o
> **parecer** segue recebendo `total_pontuais` e `total_pontuais_janela` no exec context
> (`parecer_planejador.yaml`) e emite com eles o risco *"gastos pontuais elevados sem
> política de consumo consciente formalizada"* — que **é** prescrição, ancorada 3× no
> campo contaminado. O que D1 garante é que nenhuma prescrição **determinística** a
> consome; a prescrição do LLM ainda consome. Dono: [[A40.l97]].

**Não** foi emitido campo novo para o ritmo do pontual (`pontual_mensal` — nome da
[[A40.l15]], que precede o `provisao_pontual_mensal` do co-design e prevalece por ser
o primeiro a nomear o mesmo campo): publicá-lo hoje seria imprimir um número cuja base é 57,5%
movimentação — ou, se emitido sem leitor, criar exatamente a classe
emissor-sem-leitor que a [[A40.l88]] gateia. Ele entra junto com a base limpa.
