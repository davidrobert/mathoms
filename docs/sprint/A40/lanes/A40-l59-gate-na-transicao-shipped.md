---
id: A40.l59
type: lane
title: "A transição para `shipped` ganha gate: ship_pr no frontmatter e PR visível no _README"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P2
branch_slug: a40-l59-gate-na-transicao-shipped
owner: information-architect
adrs:
  - "[[ADR-302]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p2
  - area/docs
---

# A40.l59 — `gate-na-transicao-shipped`

> **Aberta em 2026-08-12**, no fechamento da rodada de follow-ups (decisão do
> dono). Origem: o gatilho de promoção que a própria skill `lane-closeout`
> declara — *"se a classe estrutural voltar a escapar depois de N usos, aí sim
> vale promovê-la a gate na **transição** (diff que flipa `status: shipped`) —
> gatear por PR fica verde-falso quando a lane vira 2 PRs"*. O N chegou.

## Problema

A classe "PR mergeado invisível na doc da sprint" escapou o suficiente para
provar que detecção pós-merge não basta:

- No fechamento da [[A40.l7]] (2026-08-11), o `_README` não registrava o #1375 —
  **terceira ocorrência declarada na sprint**, anotada na época como candidata a
  gate.
- Nos PRs seguintes da [[A40.l34]] (#1377, #1383, #1394) o registro só não
  falhou porque foi feito **preemptivamente, por disciplina** — que é
  exatamente o que um gate existe para não depender.
- Em 2026-08-12, a nota do §Lanes do `_README` mede **10 lanes no disco fora da
  tabela** (l38–l42, l44, l45 nomeadas; l47–l49 abertas pelo #1411 sem linha) —
  a mesma classe, na direção lane→tabela.

O custo é conhecido e está medido no cabeçalho da skill: ~2,5 PRs corretivos de
doc por semana entre 2026-06 e 2026-08, porque a pergunta foi feita **depois**
do merge.

> **Relação com a §Pendência 13** (aberta em `main` pelo #1414, mesmo dia): aquela
> é sobre **alocação de id** sob paralelismo e é *owner-gated* (muda política de
> repo). Esta é sobre **registro do que já foi entregue**. Escopos distintos, mas
> a mesma raiz — 4 arquivos gerados como ponto de contenção global. Se a opção (b)
> da pendência 13 (merge driver + regeneração no pre-commit) for escolhida, o hook
> desta lane monta no mesmo lugar.

## Escopo

Hook de pre-commit disparado **pela transição**, não pelo PR:

1. Diff que flipa `status:` de uma lane para `shipped` exige, no mesmo commit:
   `ship_pr` e `ship_date` no frontmatter, **e** o PR citado presente no
   `_README` da sprint correspondente.
2. Diff que **cria** arquivo de lane exige a linha correspondente na tabela
   §Lanes do `_README` — fecha a direção que produziu as 10 órfãs.
3. O hook **não** re-implementa a `lane-closeout`: o julgamento semântico
   (números, consistência, precisão) continua na skill; o gate cobre só a
   metade estrutural que `check_closure.py` já sabe checar, movida para
   **antes** do commit.

## Critério de aceite

- **Prova retroativa**: os casos históricos (l7/#1375; as lanes órfãs do #1411)
  teriam sido barrados — reproduzir cada um contra o hook e citar o resultado.
- Polaridade certa ([[ADR-302]] e a lição da sprint): o gate **impede** o
  estado ruim de entrar, não o detecta depois.
- Gate na transição, nunca por PR — lane que vira 2 PRs não pode dar verde
  falso.
- Falso-positivo declarado: flip de `status` em rebase/revert tem escape
  documentado (a mesma classe do `--no-verify` proibido: corrigir a causa,
  nunca bypassar).

## Colisão declarada

`dev/check_closure.py` (da skill) e o hook novo compartilham a definição da
metade estrutural — extrair a checagem para módulo comum em vez de duplicar.
