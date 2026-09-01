---
id: A40.l116
type: lane
title: "O guard de autocontradição do parecer erra a seção pela terceira vez, e o teste que o cobre importa a própria constante — cego por construção"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l116-guard-de-liquidez-erra-a-secao-e-o-teste-e-cego
owner: prompt-engineer
depends_on: []
adrs: ["[[ADR-412]]"]
tags: [type/lane, sprint/a40, status/open, priority/p1, area/backend]
---

# A40.l116 — `guard-de-liquidez-erra-a-secao-e-o-teste-e-cego`

> **Origem:** `RR9-09` + `RR9-22` da rodada unificada **U5**
> ([[PIPELINE-REVIEWS-active]] §r13). **Reincidência medida** da [[A40.l80]].

## O que reincide

O parecer **elogia** *"Reserva Robusta"* e **alerta** *"Reserva Excessiva — Capital
Ocioso"* sobre o mesmo objeto, na mesma página, com `autocontradicao_removidos: 0`.

`backend/app/services/parecer_guardrails_divida.py:165` — `_SECAO_LIQUIDEZ = "S1"`. O
modelo rotula a reserva com **outra** seção. A [[A40.l80]] fechou este mesmo defeito
(#1800) quando a constante valia um **terceiro** valor: o conserto **trocou o literal** em
vez de derivar o alvo do layout, então o guard voltou a errar assim que o rótulo do modelo
mudou. **É a terceira posição em que o alvo não casa.**

## O achado novo, e ele é o que mantém o defeito vivo

`tests/test_parecer_guardrails_divida.py` **importa `_SECAO_LIQUIDEZ`** e constrói a
fixture com ele (`_risco(section=_SECAO_LIQUIDEZ)`). O teste é **invariante ao valor da
constante**: qualquer literal passa, inclusive um que o modelo nunca emite. O gate que
deveria proteger a correção da [[A40.l80]] **não pode falhar** — mesma classe dos achados
de instrumento desta rodada ([[A42.l24]]).

O contador `autocontradicao_removidos: 0` não é falso: o **detector** não alcança o par
elogio × alerta, só pares dentro da mesma lista.

## Critério de aceite

1. O alvo do guard **deriva do layout** (fonte única de `section_id`), não de um literal.
2. O teste monta a fixture com a seção que o **modelo** emite — obtida do golden, não da
   constante do módulo. Contrafactual: mudar a constante para um valor errado **reprova**.
3. O detector cobre par elogio × alerta sobre o mesmo objeto, não só pares intra-lista.
4. Tripwire: `autocontradicao_removidos == 0` com contradição presente no golden reprova.
