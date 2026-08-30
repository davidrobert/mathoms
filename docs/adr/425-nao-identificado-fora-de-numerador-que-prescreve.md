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

> ⚠️ **Emendada em 2026-08-30 (A40.l98, na implementação).** A **D4** não tinha
> régua para medir: nenhum consumidor determinístico aplica limiar a estes campos.
> Ver §Emenda 2026-08-30 no fim desta nota — a D1 e a D2 ficam intactas.

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

## Emenda 2026-08-30 — a D4 não tem régua, e por isso a D3 não foi implementada (A40.l98)

A **D4** manda medir o efeito e não o proxy: *"recalcula-se o derivado com e sem a
fatia `nao_identificado`; se as duas leituras cruzam a régua que a superfície usa
para prescrever, suprime"*. Medido na implementação, **essa régua não existe**:

| candidato a consumidor | lê `total_pontuais*` / `equivalente_meses_poupanca`? |
| --- | --- |
| `financial_score_calculator` | não |
| `risk_trigger_registry` | não |
| `pontos_fortes_analyzer` | não |
| diagnósticos comportamentais | não |
| `scoring.json::thresholds_alertas` | nenhuma chave para estes campos |

O único consumidor que **prescreve** é o parecer LLM, e ele não aplica limiar
numérico — julga "elevado" por conta própria. Sem régua não há cruzamento a
medir, e a D4 é uma condicional cujo antecedente é falso.

**A D3 fica, portanto, sem implementação — e isso é o resultado da D4, não um
atalho.** Implementá-la exigiria o limiar percentual que esta própria ADR
**rejeitou** por ser inventado; e, pior, teria **sinal trocado**. Depois da D1 o
numerador publicado é um **piso**: ele conta só o que se sabe ser consumo
discricionário, então erra para menos, que é a direção conservadora de uma
métrica de alerta. Suprimir um número verdadeiro, conservador e acionável é
exatamente a objeção que a [[ADR-422]] §Alternativas fez ao piso de
materialidade.

O que substitui a supressão é a **D2**, que já está no lugar:
`consumo_consciente.base_pontuais` publica o balde `nao_identificado` com total e
contagem ao lado do número, e a lista do card mantém as linhas. O leitor vê o
piso **e** o quanto não foi medido, que é mais informação do que um campo nulo.

**Retomar a D3** quando algum consumidor determinístico passar a aplicar régua a
estes campos — aí a D4 volta a ter o que medir. Dono: `financial-planner`.
