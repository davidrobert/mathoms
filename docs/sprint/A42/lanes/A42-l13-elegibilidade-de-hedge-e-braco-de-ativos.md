---
id: A42.l13
type: lane
title: "Elegibilidade de hedge e o braço de ativos da exposição cambial"
sprint: A42
status: planned
priority: P1
branch_slug: a42-l13-elegibilidade-de-hedge-e-braco-de-ativos
adrs:
  - "[[ADR-379]]"
  - "[[ADR-224]]"
  - "[[ADR-378]]"
tags:
  - type/lane
  - sprint/a42
  - status/planned
  - priority/p1
  - area/backend
  - area/financial-planning
---

# A42.l13 — `elegibilidade-de-hedge-e-braco-de-ativos`

> **Origem:** investigação do card Exposição Cambial (2026-08-12, workspace de
> dogfood, run `ee124571`). O P0 — o card afirmar "100% denominado em real" sobre
> R$ 83.869,92 em moeda forte — **já foi fechado** no PR #1393. Esta lane é o
> resíduo: o braço de ativos, que contribui zero desde 2026-05-19.

## O que já está decidido

[[ADR-379]] (`Proposto`) fixa a fonte: posições vêm do artefato E4 pinado ao run,
não do E5, que publica só agregados. A emenda RV2-08 da [[ADR-224]] está retratada.

## O que bloqueia a implementação

**A exclusão de cripto não cabe num `if`.** O domínio decidiu (co-design
2026-08-12) que stablecoin conta como proteção cambial e cripto volátil não — mas
`asset_catalog` dá `asset_class = "Cripto"` tanto para USDT/USDC/DAI quanto para
BTC/ETH. Excluir por classe derruba a stablecoin junto.

Ordem obrigatória, medida no dogfood:

| Cenário | Total | % investível |
|---|---|---|
| Só caixa (estado atual) | R$ 83.869,92 | 6,45% |
| Ligar o braço sem o eixo | R$ 88.434,32 | 6,80% ← conta BTC como proteção |
| Ligar o braço com o eixo | R$ 83.869,92 | 6,45% |

Ligar o encanamento antes do eixo entrega um número que o domínio **já declarou
errado**. O eixo vem primeiro.

## Passos

1. **Eixo de elegibilidade** — `asset_catalog` ganha coluna que separa "unidade de
   conta" (`lastro_moeda`, já existe) de "serve como proteção cambial". Migration
   + seed. Revisar com `data-engineer` (schema) e `financial-planner` (quais
   entradas mudam).
2. **`MIXED`/`OTHER` saem do numerador.** Hoje `_aggregate_positions` só descarta
   `BRL`, então lastro indefinido soma 100% como proteção — contra o que a
   [[ADR-224]] §6 já havia decidido. Vão para "Não-Classificada" com CTA.
3. **Loader único E4+E5 pinado ao run** ([[ADR-379]]), devolvendo value object
   tipado. `_load_latest_e5_artifact` hoje ignora o run do relatório.
4. **Atualizar o tripwire** em `backend/tests/test_exposicao_cambial_v2_api.py`
   (`test_braco_de_ativos_nao_chega_ao_endpoint_enquanto_e5_nao_publica_posicoes`)
   — ele quebra de propósito quando a fonte for ligada.

## Questões de domínio em aberto (não decidir sozinho)

- **Fundos BDR.** "Alaska Black FIC de FIA - BDR NÍVEL I" (R$ 41.846,29) e
  "Western Asset BDR FIF" (R$ 28.764,28) somam R$ 70.610,57 e classificam como
  `Fundos` → BRL. BDR replica ativo estrangeiro, então o lastro econômico é
  externo. Se contarem, a exposição deste workspace quase dobra. Não há entrada
  de catálogo nem keyword para BDR. **Ninguém decidiu isso** — o co-design de
  2026-08-12 não cobriu.
- **Catálogo inerte.** Nenhuma das 18 posições do dogfood casou o catálogo (21
  entradas); todas resolveram por `fallback_classe`. O rodapé do card promete
  "ativos com lastro econômico não-BRL" sobre um catálogo que não alcança a
  carteira real.
- **`classify_asset` erra o canônico.** `IVVB11` classifica como `FIIs`. Só não
  morde porque o catálogo tem o ticker; qualquer ETF internacional fora do
  catálogo cai em `FIIs` → BRL → fora da exposição.

## Critério de aceite

- Teste que prova por **mutação**: trocar a classe de uma posição para cripto
  volátil reduz o total; hoje não reduz. Workspace com USDT continua contando.
- Numerador ⊆ denominador por linha, não por total.
- PR registra o percentual antes/depois com o denominador corrigido. Nenhuma
  mudança aceita por "o tier melhorou".
