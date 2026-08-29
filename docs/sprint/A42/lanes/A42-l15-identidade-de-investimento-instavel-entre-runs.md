---
id: A42.l15
type: lane
title: "Identidade de investimento é hash de campos que o extrator LLM reescreve"
sprint: A42
status: planned
priority: P0
branch_slug: a42-l15-identidade-de-investimento-instavel-entre-runs
owner: data-engineer
depends_on: []
adrs:
  - "[[ADR-271]]"
  - "[[ADR-137]]"
  - "[[ADR-406]]"
tags:
  - type/lane
  - sprint/a42
  - status/planned
  - priority/p0
  - area/dados
---

# A42.l15 — `identidade-de-investimento-instavel-entre-runs`

> **Origem:** `LC6-02` da rodada unificada **U2** ([[LEDGER-CERTIFY-active]] §r6,
> merge `47970706`).

## O medido

Dois runs `completed` do mesmo workspace, mesmo corpus documental:
`investimentos_consolidados` tem 61 ids num run e 60 no outro, com **23 em comum** (38 só-A,
37 só-B) ⇒ **23,5% de estabilidade**. No mesmo par, `property_id` é **100%** estável e
`veiculo_id` é **nulo em todos** os itens.

## Mecanismo, rastreado até o produtor

`pipeline/domain/services/investimentos_dedup.py:101` — `_investment_id` é
`sha256(tipo, normalize_descricao(instituicao), normalize_descricao(descricao))[:16]`.
`normalize_descricao` (`_tx_identity.py:90`) faz lowercase + strip + collapse + sufixo PIX, e
**não colapsa** variação de sufixo societário. Os três inputs vêm **crus do item E1.5** —
saída direta do LLM, **sem passar pelo `institution_catalog` que já existe no DB**
([[ADR-137]]).

## Já refutado — não re-litigue

- A [[ADR-271]] (`Decidido`) **já** declara *"não há identidade estável"* e *"não estável a
  rename de descrição"*, e **rejeitou** o resolver com persistência (§140: *"persistir
  identidade fuzzy-derivada é gravar palpite"*). **Não proponha um.**
- O que é **novo é a classe**: a ADR previu instabilidade entre **anos** (o banco mudou o
  texto do informe). O medido é entre **dois runs do mesmo documento** — o extrator
  reescrevendo a si mesmo. A ADR nunca considerou isso.
- `property_id` é estável por ser **UUID resolvido contra o DB**
  (`db_property_identity_resolver.py`, [[ADR-215]] P2) — categoria diferente, não "campo melhor".
- Severidade é **Alto** e não Crítico porque `rg investment_id backend/app/models/
  backend/alembic/` devolve **zero**: nenhum estado persistido é corrompido.

## O dano vivo — é o que justifica o P0

`dev/compare_reviews.py` ([[ADR-406]] D7) tem **duas pernas HARD cross-run** que `corpus_grew`
não suprime: `_reclassificacao_regression:235` dispara com exatamente duas classes movendo
≥0,10pp em sinal oposto, e `_identidade_regression:253` dispara quando o número de
instituições cai. **As duas disparam com esta churn.** Um gate desenhado para pegar migração
patrimonial da família dispara com **ruído de extrator**, e o run pausa.

## Rota recomendada

Canonicalizar `instituicao` contra o `institution_catalog` ([[ADR-137]]) **antes** do hash em
`_identity_key`. É a única das três entradas que já tem catálogo no DB, resolve os dois
exemplos medidos, e **não** reabre o que a [[ADR-271]] §140 rejeitou. `tipo` e `descricao`
ficam para o PR3 que a própria [[ADR-271]] §147 deferiu.

## Critério de aceite

- Estabilidade de `investment_id` re-medida entre dois runs, com número publicado.
- As duas pernas HARD do comparador deixam de disparar sobre churn de extrator, **sem**
  deixar de disparar sobre migração real (prove com mutação).
- Provavelmente **emenda datada** à [[ADR-271]], não ADR nova.
