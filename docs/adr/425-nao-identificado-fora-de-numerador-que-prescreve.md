---
id: ADR-425
type: adr
title: "Balde não classificado fica fora de numerador que prescreve, e a cobertura da base é campo publicado"
status: Decidido
phase: A40
date: "2026-08-30"
amended_at: ["2026-08-30"]
relates_to:
  - "[[ADR-422]]"
  - "[[ADR-394]]"
  - "[[ADR-333]]"
  - "[[ADR-352]]"
  - "[[ADR-422]]"
tags:
  - type/adr
  - status/decidido
  - area/e5
  - area/dominio
  - sprint/a40
aliases: ["ADR 425", "cobertura da base", "nao_identificado"]
---

# ADR-425 — Não classificado fora de numerador que prescreve

> ⚠️ **Emendada em 2026-08-30 (A40.l98, na implementação).** A **D3** não foi
> implementada como supressão: ela é **substituída** pela degradação da prescrição,
> reusando a régua que a [[ADR-353]] já tem para o MESMO fator causal. A D1 e a D2
> ficam intactas. Ver §Emenda 2026-08-30 no fim desta nota.

**Status:** Decidido (A40.l98) • **Data:** 2026-08-30 • Co-design `financial-planner`
+ `data-engineer` + `senior-cto`. **Dono:** `financial-planner`. **Condição de
retomada:** entrega da [[A40.l98]].

## Por que ADR e não §Deferimento

A regra foi **decidida** em co-design durante a [[A40.l94]] e viveu dois dias em
**dois parágrafos de lane, nenhum em código**. §Deferimento datado responde *quando
fazer*; ADR responde *o que é verdade*. Aqui não há decisão pendente — há decisão
pendente de **implementação**, e guardá-la no mecanismo errado foi exatamente como
ela ficou invisível. A regra também é transversal: vale para o KPI de pontuais, para
o exec context do parecer e para o numerador da concentração imobiliária
([[A40.l95]] é literalmente esta classe).

## Contexto medido (2026-08-30, workspace de dogfood)

Sobre `consumo_consciente` do report `c011c40c`, com `total_pontuais_janela` =
R$ 394.525,39 — deltas **isolados por causa**, cada um com o filtro aplicado sozinho:

| recorte | Δ full | Δ janela |
| --- | --- | --- |
| ex-`transfer_categories` (aporte, [[ADR-333]]) | −R$ 190.000,00 | **R$ 0,00** |
| ex-transferência interna **detectada** | **R$ 0,00** | **R$ 0,00** |
| ex-`nao_identificado` | −R$ 348.916,19 | **−R$ 249.374,91** |

Reproduzir: agrupar `consumo_consciente.itens` por `categoria`, somando `valor`, com
e sem cada recorte; janela = itens com `mes >= fluxo_caixa.janela_12m.periodo[:7]`.

Duas consequências que reordenam o trabalho:

1. **Excluir transferência interna detectada move ZERO** — o E4 já a aplica
   (`transaction_classifier.py:361`, passo 1 do classificador). O que sobrevive em
   `nao_identificado` é o que o detector **não** pegou.
2. **A cobertura da base da janela é 36,8%** — 63,2% (R$ 249.374,91) é
   `nao_identificado`. Não é ruído a excluir: é **ausência de medição**.

## Decisão

**D1 — Não classificado não entra em numerador que prescreve.** O balde
`nao_identificado` fica no **inventário** (lista + total, rotulados) e fora de
qualquer numerador que sustente conselho.

**D2 — A cobertura da base é campo publicado, não nota de rodapé.** Onde a base
aparece, aparece com o que dela foi medido. A forma segue [[ADR-352]] e
[[ADR-394]] §D7, e o objeto publica a **identidade de conservação**:

```
bruto.valor == publicado.valor + Σ excluidos[].valor
```

`pct` **não é campo** — o leitor o deriva de `bruto`, que está no mesmo objeto.
Publicá-lo criaria um terceiro número a manter em sincronia com dois que já estão ali.

**D3 — Fora do domínio de definição, o derivado é `null` com motivo.** Abaixo do
limiar de cobertura, o número **derivado** sai `null` + `motivo_supressao`, na forma
que a [[ADR-422]] §Emenda 2026-08-30 já padronizou para `folga_nao_positiva`. O
**inventário continua publicado** — é factual.

**D4 — O limiar é medido, não constante.** Recalcula-se o derivado com e sem a fatia
`nao_identificado`; se as duas leituras **cruzam a régua que a superfície usa para
prescrever**, suprime. Mede o efeito, não o proxy.

> **Alternativa rejeitada — o limiar percentual.** O co-design da [[A40.l94]] chegou a
> sugerir ~30%, e o autor o **retirou**: a própria [[ADR-422]] §Alternativas acabara de
> matar um limiar (`1,15` do teto) pelo argumento de que era inventado, e propor outro
> no dia seguinte sem origem declarada repetiria o defeito. Se a implementação precisar
> de constante por simplicidade, o valor com origem declarável é **50%** — a fronteira
> entre "majoritariamente medido" e "majoritariamente não medido", isto é, o ponto em
> que o derivado descreve mais o desconhecido que o conhecido. Escreva a frase, e o
> limiar deixa de ser inventado.

## Consequências

- **Suprimir não degrada o diagnóstico — o converte em ação.** *"R$ 394 mil em
  lançamentos pontuais, dos quais R$ 249 mil ainda não classificados"* faz a família
  olhar os próprios lançamentos, que é o único caminho para a contaminação sair sem
  depender do detector. É porta de entrada do Categorization Learning Loop.
- **A regra não conserta a detecção, e isso é deliberado.** Adicionar padrão de
  transferência move um número publicado sem que nada tenha acontecido no mundo da
  família — a mesma objeção que a [[ADR-422]] D3 fez ao denominador editável. Com D2/D3
  no lugar, melhorar a detecção vira melhoria **monotônica** da cobertura.
- **Ordem:** D2 é **pré-requisito**, não consequência — é ele que permite publicar
  honestamente com base ruim. Não o adie esperando a base melhorar.

## Emenda 2026-08-30 — a D3 vira degradação de prescrição, não supressão (A40.l98)

> **Correção de uma afirmação desta própria emenda.** A primeira versão dizia que
> *"a régua não existe"* e concluía que a **D4** era condicional de antecedente
> falso. **É falso**, e o erro foi de recorte: procurei consumidor determinístico
> de `total_pontuais*` e de `equivalente_meses_poupanca` — e não de régua sobre o
> **fator causal**, que é o share de `nao_identificado`. Refutado pelo
> `financial-planner` na revisão da [[A40.l98]].

**A régua existe, e é da [[ADR-353]]:**

```
pipeline/domain/services/diagnostico_comportamental_analyzer.py
NAO_IDENTIFICADO_PARCIAL_PCT      = 10.0
NAO_IDENTIFICADO_INSUFICIENTE_PCT = 30.0
```

Não é constante solta: `_apply_confianca_gate` **substitui o diagnóstico
comportamental inteiro** acima de 30%, `kpi_target_catalog` publica o alvo, e o
parecer já recebe `$.diagnostico_confianca.nivel` com o hint *"'insuficiente' torna
a prescrição provisória"*. O *"~30% sem origem declarável"* que a §Alternativas
desta ADR rejeitou por inventado **é literalmente esse 30,0**, escrito meses antes.

## O que decide a forma do remédio

Suprimir continua **rejeitado**, mas por um motivo que só vale para uma metade do par:

| campo | efeito da cobertura baixa | direção do erro |
| --- | --- | --- |
| `total_pontuais` / `_janela` | piso do consumo discricionário identificado | **conservador** — alarma menos, mas é verdadeiro e acionável |
| `equivalente_meses_poupanca` | massa faltante está **só no numerador** | **tranquilizador** — publica 4,0 onde a verdade pode ser 11 |

O argumento *"piso é a direção conservadora de uma métrica de alerta"* **não
transfere** para a razão: ela não é piso de nada, é razão de direção conhecida e
magnitude desconhecida, com uma casa decimal que aparenta precisão. Mas suprimi-la
esbarra na objeção que a [[ADR-422]] §Alternativas fez ao piso de materialidade —
o número suprimido seria verdadeiro e acionável.

**D3.a — a cobertura degrada a PRESCRIÇÃO, não apaga o número.** Nenhum campo é
suprimido. O que muda é que a base passa a viajar **junto** do número, na superfície
que prescreve, e o veredito ordinal de cobertura reusa as constantes da [[ADR-353]] —
a mesma régua, não um limiar novo. É o padrão que o produto já usa para este exato
fator causal.

**D2 tinha implementação incompleta, e isso era o defeito operante.** A versão
anterior desta emenda dispensava a D3 alegando que *"a D2 já está no lugar"*. Estava
— **só no card React**. O parecer LLM não tem `tools`: o manifest é a superfície
inteira dele, e `base_pontuais` não estava lá. Ele recebia `total_pontuais*` já
reduzido pelos filtros da [[A40.l98]] sem nenhum sinal de que virara piso, o que
trocaria over-alarm por **under-alarm silencioso** na única superfície que prescreve.
Corrigido no #1865: a base bruta e o balde `nao_identificado` (valor + contagem)
entram no exec context, os rótulos dos dois totais declaram que são piso, e um hint
manda classificar antes de cortar.

**Deferido com dono:** o campo ordinal `base_pontuais.cobertura_nivel ∈ {alta,
parcial, insuficiente}`, derivado de `excluidos.nao_identificado.valor / bruto.valor`
**importando** as constantes da [[ADR-353]] (nunca redeclarando-as). A população aqui
é mais estreita que a da ADR-353 — só lançamentos acima do limiar —, e essa diferença
precisa ficar declarada no docstring. Dono: `financial-planner`.

### Cobertura: qual razão, exatamente

`publicado / bruto` **não** é a cobertura desta ADR. O 36,8% medido acima é
`publicado / (publicado + nao_identificado)` — a razão entre *o que foi medido* e *o
que era medível na mesma natureza*. `recorrente` e `transferencia_*` não são falha de
medição: são exclusão correta e deliberada. Com o `bruto` largo (todo lançamento acima
do limiar), `publicado / bruto` no dogfood cai para a casa de 10-15% e não é cobertura
de coisa nenhuma. Refutação do `senior-cto` na revisão da [[A40.l98]].
