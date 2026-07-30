---
id: A40.l12
type: lane
title: "Classificação incompleta distorce KPI: mecanismo de aporte inerte + não-identificado material"
sprint: A40
plan: PLAN-report-trust
status: planned
priority: P1
branch_slug: a40-l12-classificacao-incompleta-distorce-kpi
adrs: ["[[ADR-351]]"]
depends_on: ["[[A40.l1]]"]
tags:
  - type/lane
  - sprint/a40
  - status/planned
  - priority/p1
  - area/pipeline
---

# A40.l12 — `classificacao-incompleta-distorce-kpi` (RV3-20, RV3-21)

## Problema

**Mecanismo inerte (RV3-20).** O balde de aporte está vazio na janela ⇒ o mecanismo
`despesa_consumo = total − aporte` é **no-op**, e `despesa_consumo == despesa_total`.
A taxa de poupança é não-confiável **por construção**, e o relatório a exibe com
veredito.

**Não-identificado material (RV3-21).** O share por **valor** cruza o limiar de
degradação na janela curta (maior que na janela longa). A [[ADR-353]] degrada mas
não bloqueia, e falta pouco para o patamar seguinte.

**Direção:** ambos empurram para o lado **otimista** — parte do viés direcional
agregado (§Decisões nº 5 do sprint).

## Escopo

- Flip de [[ADR-351]] (retorno de principal não é renda recorrente) — medir a
  materialidade primeiro, com o instrumento da [[A40.l1]].
- Segregar o balde de aporte; witness entrada↔saída por instituição.
- Contrato novo: `ratios.taxa_poupanca.status ∈ {ok, base_incompleta, indisponivel}`
  + `base_flags[]`. **`status` é derivado, nunca autorado** — emitido pelo mesmo
  calculator que produz o número.

## Critério de aceite

- Unit no enricher: fixture com aporte vazio ⇒ `status == "base_incompleta"` + flag
  correspondente.
- Fixture com share acima do limiar ⇒ flag correspondente.
- **A UI não exibe veredito quando `status != ok`** — exibe o número com a ressalva,
  ou não exibe.
- Declarar o sinal esperado do delta: a correção move a taxa de poupança **para
  baixo**. Se `dev/golden_diff.py` mostrar subida, o fix está errado.

## Guarda anti-regressão

`status` derivado é o invariante que impede "taxa de poupança exibida com veredito
sobre base não-confiável" de voltar. Se alguém autorar `status` manualmente, o teste
do calculator quebra.
