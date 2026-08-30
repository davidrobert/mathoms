---
id: A42.l22
type: lane
title: "A previsão de tempo exibida durante o run é subdeclarada em até 72%: a mediana mistura no-ops de milissegundos com execuções de minutos"
sprint: A42
status: open
priority: P2
branch_slug: a42-l22-mediana-de-duracao-mistura-no-op
owner: sre-devops
depends_on: []
adrs: ["[[ADR-342]]"]
tags: [type/lane, sprint/a42, status/open, priority/p2, area/dados]
---

# A42.l22 — `mediana-de-duracao-mistura-no-op`

> **Origem:** `PV12-01` da rodada unificada **U4** ([[PIPELINE-REVIEWS-active]] §r12).
> **É o único P2 desta rodada com consequência medida na superfície do usuário.**

## O defeito

`pipeline_stage_log_repository.get_median_durations_for_workspace` filtra
`status == 'completed'` e, com isso, inclui na mediana os stages que **se auto-declararam
no-op** (`output_summary.skipped == true`) mas gravaram `completed` na coluna. No-op roda
em **milissegundos**; execução real leva **minutos**. A mediana resultante vira a **ETA
exibida durante a execução**.

## Medição — e ela é o falsificador que o próprio cético prescreveu

O cético do lote B enunciou: *"medir a mediana por stage com e sem as linhas de flag — se a
ETA dos `extract_*` não se mover, o achado fica confinado ao `run_scope` e é duplicata pura
do já-conhecido"*. **Rodada. Ela se move:**

| stage | mediana COM no-op | mediana SEM | erro |
|---|---|---|---|
| `extract_comprovantes_bens` | 15.030 ms | 53.358 ms | **−71,8%** |
| `extract_baseline` | 322.317 ms | 382.270 ms | **−15,7%** |
| `extract_informes_anuais` | 75.529 ms | 77.072 ms | −2,0% |
| `extract_irpf_full` | 333.470 ms | 334.870 ms | −0,4% |

Um stage tem ETA **3,5× otimista** para quem está esperando o run terminar.

## Relação com o registro

`PV9-02` registra que a coluna `status` não reflete o skip — e o cético mostrou que as duas
populações são **eventos distintos e deliberadamente separados** no produtor (15 são decisão
pré-execução do orquestrador; 21 são no-op auto-declarado). **Esta lane não é sobre
unificá-las:** é sobre o **consumidor não-interno** que ninguém tinha nomeado.

## Critério de aceite

- [ ] O predicado da mediana exclui linha cujo `output_summary` declara `skipped`, ou a ETA
      passa a declarar que é piso.
- [ ] **Controle:** recomputar as medianas com e sem as linhas de flag e verificar que o
      delta caiu a zero nos stages medidos acima.
- [ ] Não mexer na separação `completed`/`skipped` da coluna — é decisão do produtor e está
      fora desta lane.
