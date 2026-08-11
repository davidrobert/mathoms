---
id: A40.l36
type: lane
title: "Double-count potencial na base da cascata fiscal da S8: pró-labore pode entrar duas vezes"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l36-double-count-base-cascata-s8
adrs:
  - "[[ADR-236]]"
  - "[[ADR-375]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/pipeline
  - area/financial-planning
---

# A40.l36 — `double-count-base-cascata-s8`

> **Aberta em 2026-08-11**, achado do co-design da [[A40.l34]] (`senior-cto`).
> Registrada como §Não-objetivo da [[ADR-375]] para não inchar aquela lane.
> **Não medida ainda** — o achado é de leitura de código, e a lane começa
> confirmando ou refutando.

## Problema (a confirmar)

`cascata_calculator.py:383` compõe a base PF como
`cargas.bruto_anual` (pró-labore anualizado) `+ outras_rendas_tributaveis_pf_anual`.
O segundo termo é preenchido por `tributario_input_builder._assemble_input` a
partir de `_load_irpf_renda_tributavel`, que é o **total** de rendimentos
tributáveis do IRPF.

**Se o total do IRPF já contém o pró-labore, a base da S8 soma duas vezes.**

Isto importa mais depois da [[ADR-375]], não menos: aquela ADR faz da S8 a
**dona única** do limite PGBL publicado. Um defeito na base da S8 deixa de ter
uma segunda opinião no documento para contradizê-lo.

## Escopo

1. **Medir primeiro.** Confirmar se `_load_irpf_renda_tributavel` inclui a ficha
   de pró-labore. O achado é de leitura; pode não reproduzir.
2. Se reproduzir: decidir quem é a fonte do pró-labore quando as duas existem —
   é regra de domínio, gatilho de `financial-planner`.
3. O defeito é do produtor da S8 e cai **dentro** da [[ADR-236]]: emenda datada,
   não ADR nova, salvo se a decisão mudar a base declarada.

## Critério de aceite

- Medição registrada, com o caso que reproduz **ou** a refutação datada.
- Se reproduzir: teste com pró-labore presente nas duas fontes, provando a
  contagem única.
- Delta declarado e conferido por `dev/golden_diff.py` — a base cairia, então o
  sinal é `↓`.

## Colisão declarada

Toca `cascata_calculator.py`, que a [[A40.l34]] **não** modifica (a l34 só
consome a base). Sem colisão de conteúdo; quem mergear depois rebaseia.
