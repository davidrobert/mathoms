---
id: ADR-428
type: adr
title: "A direção conservadora de um piso é fixada pelo uso do número, não pelo número"
status: Decidido
phase: A40
date: "2026-08-31"
relates_to:
  - "[[ADR-425]]"
  - "[[ADR-422]]"
  - "[[ADR-353]]"
  - "[[ADR-394]]"
  - "[[ADR-136]]"
tags:
  - type/adr
  - status/decidido
  - area/e5
  - area/dominio
  - sprint/a40
aliases: ["ADR 428", "provisao pontual mensal", "piso que prescreve"]
---

# ADR-428 — A direção conservadora de um piso é fixada pelo uso

**Status:** Decidido • **Data:** 2026-08-31 • Decisão do `financial-planner`, dono
declarado da [[A40.l98]]. Fecha o único item dos três deferidos pela [[A40.l94]] que
ficou sem lane e sem dono — achado do closeout da [[A40.l98]].

## Contexto

A [[A40.l15]] definiu `consumo_consciente.pontual_mensal = pontuais_janela / n_meses`
— *"o ritmo do gasto pontual"*. A [[ADR-422]] §Consequências decidiu **não** emiti-lo
*"porque a base é 57,5% movimentação"*, e prometeu: *"Ele entra junto com a base
limpa."*

A base limpa entrou (#1865). E foi **ela** que tornou o campo impublicável: desde a
[[ADR-425]] §D1, `total_pontuais*` exclui o balde `nao_identificado` — R$ 249.374,91,
63,2% da janela no dogfood. O numerador virou **piso**.

## A tabela da [[ADR-425]] tinha uma terceira linha

| campo | efeito da cobertura baixa | direção do erro | a família |
| --- | --- | --- | --- |
| `total_pontuais*` | piso do consumo identificado | **conservador** — alarma menos, e é verdadeiro | **lê** |
| `equivalente_meses_poupanca` | massa faltante só no numerador | **tranquilizador** | **lê** |
| **provisão mensal do pontual** | **piso de uma prescrição de acúmulo** | **tranquilizador, e invisível como piso** | **executa** |

## Decisão

**D1 — A direção conservadora de um piso é determinada pelo USO do número.** Para
métrica de **alerta**, piso alarma menos e continua verdadeiro e acionável. Para
métrica de **provisão**, piso é **sub-provisão** — e sub-provisão é o mecanismo pelo
qual o aporte quebra no primeiro evento, que é o dano que a [[ADR-422]] §Contexto
documentou ao matar a folga inflada. A regra é transversal: vale para qualquer
métrica-piso futura, e alcança a concentração imobiliária da [[A40.l95]].

**D2 — `pontual_mensal` não é emitido.** Não pelo argumento de emissor-sem-leitor
(esse caiu: a prosa do E5 já imprime *"Na janela de N meses são R$ X"* e o card a
renderiza, então o ritmo **já é derivável** pelo leitor). Não é emitido porque seu
único uso é prescritivo e o piso não sustenta prescrição de acúmulo.

**Condição de retomada, cumulativa:** `cobertura_nivel == alta` **e**
`janela_meses == 12`. Fora disso, `null` + `motivo_supressao`.

**D3 — O teto também não serve.** `(publicado + nao_identificado)/n` dá R$ 32.877/mês
no dogfood contra piso de R$ 12.096 — banda de **2,7×**. Provisionar pelo teto faria a
família guardar contra R$ 194.886,65 que nomeiam outro banco do próprio titular e
R$ 32.000 de conversão BRL→USD, e — pior — **removeria o incentivo de classificar**,
que é a única saída da contaminação ([[ADR-425]] §Consequências). **Com 36,8% de
cobertura não existe número de provisão defensável; a largura da banda é o achado.**

**D4 — Se um dia embarcar, chama-se `provisao_pontual_mensal`.** A [[A40.l15]] fixou
`pontual_mensal` **por precedência**, não por semântica, e precedência não sobrevive à
mudança de ato de fala do campo. Este card já foi mordido duas vezes por rótulo que não
bate com o que o número faz ([[ADR-422]] D2 e §Emenda) — esta seria a terceira, e desta
vez sabe-se antes de emitir.

**D5 — O denominador é `n_meses`, e ele não é escolha independente.** Mediana dá R$ 0
no mês típico: descreve bem e não serve para nada. A média é exatamente o cálculo de um
*sinking fund* — total do ciclo ÷ meses do ciclo. **Escolher `n_meses` é escolher a
leitura de provisão**, então D2 e D5 são a mesma decisão. E `n` tem de ser **12**: a
origem do limiar não é estatística, é a **periodicidade do fato** (IPVA, IPTU, seguro,
matrícula, férias ocorrem uma vez por ciclo anual). Com `n < 12` a média roda sobre
ciclo incompleto e o erro **não tem sinal conhecido** — estimador de sinal desconhecido
é pior que estimador nenhum quando a família age sobre ele.

**D6 — A provisão correta é prospectiva, e não é do E5.** Quais eventos, quando, quanto
— isso é `Decision` / Plano de Ação ([[ADR-136]]), onde meta é o objeto. O estimador
retroativo será sempre proxy.

## Ordem

`base_pontuais.cobertura_nivel` ([[ADR-425]] §Emenda) vem **primeiro e sozinho**. Se
viesse junto, o ritmo nasceria `null` em **todos** os corpora que existem: no dogfood
por cobertura (63,2% > 30,0% ⇒ `insuficiente`) e no substrato versionado porque
`consumo_consciente` é todo zero. Campo sempre nulo no corpus de referência é
emissor-sem-leitor com passos extras.

## Consequências

- A promessa da [[ADR-422]] §Consequências (*"entra junto com a base limpa"*) fica
  **falsa** e é emendada lá, com data.
- A [[A40.l15]] (`cancelled`) e o §Achado do closeout da [[A40.l98]] passam a apontar
  para esta nota — **por wikilink**, não por código de achado: foi ser "código, não
  wikilink" que deixou `LC6-05` apontando para lane inexistente e `PV9-12` invisível ao
  `check_closure`.
- **Achado colhido junto, e consertado no mesmo PR:** `base_pontuais` é **full-period**
  (`_triar` não tem filtro de janela), e o manifest 2.14.0 o pareava com
  `total_pontuais_janela` sob rótulo *"mesma base"*. Corrigido em 2.15.0 — os quatro
  rótulos declaram o escopo temporal, que é o que a [[ADR-306]] D1 exige.
