---
id: A42.l20
type: lane
title: "O contador de linhas do E3 ignora o canal de remoção que a função vizinha lê, e o resultado sai com duas causas declaradas, ambas falsas"
sprint: A42
status: open
priority: P2
branch_slug: a42-l20-contador-do-razao-ignora-canal-de-remocao
owner: data-engineer
depends_on: []
adrs: ["[[ADR-342]]", "[[ADR-347]]"]
tags: [type/lane, sprint/a42, status/open, priority/p2, area/dados]
---

# A42.l20 — `contador-do-razao-ignora-canal-de-remocao`

> **Origem:** `LC8-03` da rodada unificada **U4** ([[LEDGER-CERTIFY-active]] §r8).

## O defeito

`dev/ledger_certify_core.py` — `_e3_count` soma apenas
`transacoes_total + transacoes_duplicadas_removidas` e **ignora `remocoes`**, embora
`_ledger_verdict`, **duas funções acima no mesmo arquivo**, leia `remocoes`. Um canal de
remoção **declarado e reconciliável ao inteiro** sai então como *count divergente*.

O custo não é o número errado: são as **duas causas declaradas junto do diagnóstico**
(*"keying mudou pós-run"* e *"run parcial"*), **ambas falsas** para este caso. Quem lê o
relatório do razão é mandado investigar duas hipóteses que não se aplicam.

## O que a `U4` já mediu, e o que ela refutou

Os déficits dos 4 grupos com `count divergente` somam **exatamente 907** — o mesmo 907 que
o `X3b` certifica como consolidação executada pelo run, e são os **únicos 4** com
`remocoes.cross_document_collapse ≠ 0`.

**A leitura inicial de que o sinal era o oposto do previsto foi REFUTADA pelo cético:** o
harness chama `_e3_build_adapter` **sem** `collapse_enforce` (default `False`), e o adapter
só corta sob `if self._cross_document_collapser and self._collapse_enforce`. O lado fresco
**mede** os removíveis e **não remove** — o sinal é exatamente o previsto.

## Critério de aceite

- [ ] `_e3_count` normaliza por `remocoes`, ou declara por escrito que não o faz e a causa
      "canal declarado" entra na lista de causas.
- [ ] As duas causas declaradas deixam de ser emitidas quando o canal explica o delta ao
      inteiro.
- [ ] **Controle:** normalizar e re-executar — se `count divergente` cair a **0**, a
      divergência era 100% de configuração; resíduo remanescente é drift de verdade e
      merece as causas atuais.

## Fora de escopo

A perna de valor inerte é da [[A42.l18]]; o guard de escrita é da [[A42.l19]].
