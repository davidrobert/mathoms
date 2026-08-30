---
id: A40.l108
type: lane
title: "Um mesmo ano nomeia o cenário central e o de estresse, enquanto o cenário base do mesmo apêndice é outro"
sprint: A40
status: open
priority: P2
branch_slug: a40-l108-um-ano-nomeia-cenario-central-e-de-estresse
owner: financial-planner
depends_on: []
adrs: []
tags: [type/lane, sprint/a40, status/open, priority/p2, area/produto]
---

# A40.l108 — `um-ano-nomeia-cenario-central-e-de-estresse`

> **Origem:** `RR8-03` da rodada unificada **U4** ([[REPORT-REVIEWS-active]] §r8).
> **Residual afiado que o enunciado original perdeu** — o cético refutou a formulação
> inicial e, ao refutá-la, achou o defeito real.

## O que foi refutado, primeiro

O enunciado dizia *"três anos de IF publicados sem rótulo que os distinga"*. **Cai:** o
prazo declarado é rotulado como tal **3×**, o central é rotulado "cenário central", e o
apêndice opõe base vs. estresse com delta explícito.

## O defeito que sobrou, e ele é mais estreito e mais afiado

**O mesmo ano nomeia duas coisas não relacionadas:**

| onde | o que aquele ano significa |
|---|---|
| Projeção Patrimonial — 3 Cenários | o **cenário central** estocástico (entre favorável e adverso) |
| Cenários de Estresse — sem segunda renda | o **cenário de estresse** (`+1 ano` sobre a base) |
| Apêndice C — cenário **base** | um ano **anterior** aos dois acima |

São **dois motores de projeção com anos-base diferentes** — determinístico e estocástico —
colidindo no ano que o leitor não consegue classificar. Quem lê não tem como saber se aquele
ano é o resultado **esperado** ou o **degradado**; e o cenário rotulado "base" aponta para
outro.

## Critério de aceite

- [ ] Existe **precedência declarada** entre os dois motores, ou os dois anos passam a
      carregar qualificador de motor no ponto de leitura.
- [ ] **Teste de leitura:** perguntar *"qual é o seu ano de independência financeira?"* — se
      o leitor citar o ano colidido sem saber a qual dos dois se refere, a colisão é o item.
- [ ] O par de progressos (capa vs. demais sítios) é arredondamento de exibição e **não**
      entra nesta lane — já re-escopado em `RR6-28`.

## Relação com o registro

`RV3-14` já registra que a capa imprime o ano **sem qualificador de cenário**. A
**colisão entre central e estresse** é nova.
