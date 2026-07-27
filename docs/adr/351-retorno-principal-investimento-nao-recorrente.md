---
id: ADR-351
type: adr
title: "Retorno de principal de investimento não é renda recorrente (receita_investimento)"
status: Proposto
phase: ledger-certify r3
date: "2026-07-27"
relates_to:
  - "[[ADR-333]]"
  - "[[ADR-090]]"
  - "[[ADR-143]]"
  - "[[ADR-347]]"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
---

# ADR-351 — Retorno de principal de investimento não é renda recorrente

> Achado **LC03** da certificação `ledger-certify` r3 (camada B, fronteira de
> classificação — cega à conservação). **Espelho do [[ADR-333]]** no lado da
> **receita**: o ADR-333 tirou o *aporte* do consumo; este tira o *retorno de
> principal* da renda recorrente. `Proposto` — a implementação runtime é **gated**
> (ver §Consequências): muda um número exibido (taxa de poupança) e exige medição
> de materialidade + revisão do dono antes de shipar.

## Contexto

`receita_investimento` **não** está em `_DEFAULT_ONE_TIME_CATEGORIES`
(`fluxo_caixa_enricher.py:47`) — logo entra em `receita_recorrente`, numerador de
`taxa_poupanca_recorrente` (`fluxo_caixa_enricher.py:453`). Na certificação r3 de
um workspace de dogfood, `receita_investimento` respondeu por **304 de 776 tx de
receita (~39%)**.

Num perfil pesado em renda fixa, o **vencimento/resgate de um título devolve
principal + juros na mesma linha de crédito**. Se o crédito inteiro cai em
`receita_investimento` (tratado como recorrente), a parcela de **principal** —
que é devolução de patrimônio, não renda — vira **renda-fantasma recorrente**.
Efeito: infla `receita_recorrente` e puxa a taxa de poupança para cima (direção
**otimista**, que dá falso conforto — o pior sentido do erro).

O balde não distingue **rendimento** (juros/dividendo/JCP/cupom = renda passiva
recorrente legítima) de **retorno de principal** (transferência patrimonial) e de
**ganho realizado** (evento one-time). A conservação de valor não vê isto: o total
de receitas fecha por construção — é fronteira de classificação (camada B).

**Insulação (verificada na r3):** `passive_income_calculator.py` (renda passiva /
TRS) e `if_projector.py` (projeção de independência) derivam do IRPF e das metas,
**não** das receitas categorizadas do E4. Logo este erro corrompe **apenas fluxo
de caixa + taxa de poupança** — nunca patrimônio, TRS ou projeção-IF. É **P1 de
fluxo, não P0 patrimonial**.

## Decisão

**Retorno de principal em resgate / vencimento / liquidação / amortização é
transferência patrimonial (ou ganho realizado one-time), NÃO renda recorrente.**
Simétrico ao [[ADR-333]] (aporte = transferência, não consumo).

1. **Ônus da prova no balde recorrente.** Só entra em `receita_recorrente` o
   crédito com **descritor inequívoco de rendimento** (juros, dividendo, JCP,
   cupom, rendimento de aplicação). Rendimento genuíno permanece renda recorrente
   — é o retorno que a metodologia de planejamento patrimonial trata como renda.
2. **Fallback conservador.** Descritor **ambíguo** (não claramente rendimento) →
   fora do recorrente (one-time / transferência), marcado `needs_review`. O
   sistema prefere subestimar renda recorrente a inventá-la.
3. **Regra universal de domínio ([[ADR-143]], methodology-as-code):** a regra vive
   em docstring co-localizada com o enforcer (`fluxo_caixa_enricher` /
   classificador) + esta ADR canônica; dado de cliente continua no DB.

## Alternativas consideradas

- **(a) Jogar `receita_investimento` inteiro em one-time.** Rejeitada: apagaria
  dividendo / JCP / cupom, que **são** renda passiva recorrente — sub-contaria a
  renda real. Erro na direção oposta, ainda errado.
- **(b) Manter como está (tudo recorrente).** Rejeitada: é o defeito — renda-
  fantasma otimista de principal.
- **(c) Split por semântica de descritor + fallback conservador.** **Escolhida** —
  separa rendimento (recorrente) de principal/ganho (não-recorrente) pelo sinal
  mais confiável disponível (descritor), com o ônus da prova no lado que infla.

## Consequências

- **Implementação gated (não conforma-e-mergeia).** Antes do PR de runtime:
  (i) **medir materialidade por valor** — quanto de `receita_investimento` é
  principal vs rendimento (o witness de round-trip por instituição do harness
  `ledger-certify`, achado F8/LC01, quantifica); (ii) **revisão do dono**, pois
  muda a `taxa_poupanca` exibida. Sem a medição, o corte de descritor é palpite.
- **Par obrigatório com o lado do aporte (F4 da r3).** Emenda datada ao [[ADR-333]]
  precisa firmar a precedência `aporte_investimento` × transferência genérica no
  classificador **e a simetria do round-trip** (aporte que sai e principal que
  volta se cancelam no fluxo; a variação aparece no balanço/baseline, não no
  fluxo). **Ordem obrigatória: F3 antes de F4, ou juntos** — F4 sozinho (aporte
  visível saindo, principal ainda entrando como renda) **amplifica** o otimismo.
- **Reconciliar vocabulário.** O hint LLM (`rendimento_aplicacao`) e a categoria de
  regra (`receita_investimento`) precisam casar para não gerar categoria órfã.
- **Não toca conservação nem patrimônio/TRS/IF** (insulação acima). Sem bump de
  `score_version` — a taxa é input do score, não a fórmula (mesmo racional do
  [[ADR-333]]).
