---
id: A42.l20
type: lane
title: "O contador de linhas do E3 ignora o canal de remoção que a função vizinha lê, e o resultado sai com duas causas declaradas, ambas falsas"
sprint: A42
status: shipped
ship_pr: 1907
ship_date: "2026-08-31"
priority: P2
branch_slug: a42-l20-contador-do-razao-ignora-canal-de-remocao
owner: data-engineer
depends_on: []
adrs: ["[[ADR-342]]", "[[ADR-347]]"]
tags: [type/lane, sprint/a42, status/shipped, priority/p2, area/dados]
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

- [x] `_e3_count` normaliza por `remocoes` — via `declared_removed_count`
      (ex-`_declared_removed_count`), o **mesmo** normalizador da conservação E2→E3.
      Degrada ao campo legado quando o artefato não declara `remocoes`.
- [x] As duas causas declaradas deixam de ser emitidas quando o canal explica o delta ao
      inteiro — o grupo deixa de entrar em `count_diff`. Os quatro sítios que declaravam a
      lista ganharam a **terceira** causa que faltava (config do harness ≠ config do run).
- [x] **Controle** — ver §Controle A/B abaixo: `count divergente` caiu a **0**, resíduo zero.

## Controle A/B (2026-08-31)

Mesmo DB, mesmo workspace (`1b9f2cf5`), mesmo run pinado (`7d860f0b`); só o código muda.

| | grupos casados | count divergente |
|---|---|---|
| antes (`1a7aa0c1`) | 108 | **4** |
| depois | **112** | **0** |

Os 4 déficits — `c6bank_…202506` 271 · `c6bank_…202507` 128 · `c6bank_…202508` 440 ·
`itau_…202507` 68 — somam **907**, o mesmo 907 do `X3b`. A divergência era **100% de
configuração**; resíduo após normalizar: **zero**.

**O risco da própria mudança foi medido, não suposto.** Normalizar soma *todos* os canais
dos dois lados, então grupo que antes casava poderia passar a divergir se as pontas
discordassem em `undated`/`anachronic`/`intra`. Não aconteceu: 108 + 4 = 112, nenhum grupo
migrou para divergente. O teste `test_drift_ainda_acusa_divergencia_que_o_canal_nao_explica`
congela a não-inércia no outro sentido — resíduo fora do canal continua acusado.

Os 31 "só no persistido" não se movem (sobra de 7 outros runs, `LC6-01`).

## Uma linha do enunciado envelheceu

*"`_ledger_verdict`, **duas funções acima no mesmo arquivo**"* era verdade na `U4`: a
[[A42.l19]] (`5504d91c`) extraiu a rubrica para `dev/ledger_unit_verdicts.py` **depois**
da medição. O defeito descrito não muda — dois módulos liam `remocoes` e o terceiro não —
mas quem for atrás da citação não a encontra onde ela diz.

## Fora de escopo

A perna de valor inerte é da [[A42.l18]]; o guard de escrita é da [[A42.l19]].
