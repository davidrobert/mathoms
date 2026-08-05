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

## Itens adotados (2026-08-05)

Follow-ups órfãos da [[A40.l4]] §Residual, roteados para esta lane pela triagem de
destino da A40 (mesmo arquivo `e5_analyzer_adapter.py`, classe de risco "número
exibido descontrolado por config/balde incompleto"). **Não agrupados numa lane
própria**: o critério da sprint é "arquivo compartilhado **e** risco compartilhado",
e os dois riscos abaixo são distintos — ficam como itens separados desta lane, cada
um com critério de aceite e sinal de delta próprios, para não repetir a lição da
l30/l31 (lane com risco misto vira infechável).

### Item A — DAS ausente em `s8`/`despesas_impostos` (ex-`A40.l4` §Residual)

`_DAS_KEYWORDS` tinha 1 keyword ambígua (casava a preposição "das", 100%
falso-positivo no dogfood) até o commit `69a2fad4` (#1133, 2026-07-31), que a
substituiu por 6 keywords unívocas. A [[A40.l4]] mergeou **antes** de re-medir o
balde com o matcher novo, e por isso não afirma DAS (estimado ou recolhido) nem
soma `das_simples` em `despesas_impostos` — decisão correta na ausência da medição.

- **Gate em duas etapas, nesta ordem:** (1) medir a precisão do balde `das_simples`
  no corpus dogfood com o matcher de `69a2fad4`; (2) **somente se** a precisão for
  alta, somar em `despesas_impostos` e reintroduzir a afirmação no `s8`.
- Se a medição não sustentar reintrodução, o item fecha declarando **teto
  estrutural** (vocabulário KR-A da A42), não dívida aberta.
- Sinal de delta esperado: `↑` em `despesas_impostos` **se e somente se** a etapa 1
  passar — declarar no PR; `dev/golden_diff.py` confere.

### Item B — PD-20: meta de TRS não é configurável (ex-`A40.l4` §Residual)

`RatiosCalculator()` roda com `RentabilidadeConfig()` default (5,0%);
`PassiveIncomeConfig.trs_meta_pct`, construído do goal do cliente, nunca é lido.
`S7IndependenciaSection.tsx` imprime o default, não a meta real da família.

- Ler `trs_meta_pct` do config já construído (`e5_analyzer_adapter.py:1148` já
  monta `PassiveIncomeConfig` a partir do goal — o fio já está pago).
- **Bound explícito:** o wizard aceita `trs_pct` 0–20. Fora de faixa razoável ⇒ usa
  a referência de 5% e **declara qual usou** — não propagar meta absurda ao
  cálculo.
- Micro-gate `financial-planner` no PR (só o bound de faixa), não co-design de
  sessão.
- Sinal de delta: variável por workspace, mas **declarado por caso** — a mudança é
  cliente-a-cliente, não sistemática.
