---
id: A42.l22
type: lane
title: "A previsão de tempo exibida durante o run é subdeclarada em até 72%: a mediana mistura no-ops de milissegundos com execuções de minutos"
sprint: A42
status: shipped
ship_pr: 1959
ship_date: "2026-09-01"
priority: P2
branch_slug: a42-l22-mediana-de-duracao-mistura-no-op
owner: sre-devops
depends_on: []
adrs: ["[[ADR-342]]", "[[ADR-119]]", "[[ADR-357]]"]
tags: [type/lane, sprint/a42, status/shipped, priority/p2, area/dados]
---

# A42.l22 — `mediana-de-duracao-mistura-no-op`

> **Origem:** `PV12-01` da rodada unificada **U4** ([[PIPELINE-REVIEWS-active]] §r12).
> **É o único P2 desta rodada com consequência medida na superfície do usuário.**
> ⚠️ **Esta linha caiu na entrega** — o stage medido não emite ETA. Ver
> §Duas linhas do enunciado envelheceram.

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

- [x] O predicado da mediana exclui linha cujo `output_summary` declara `skipped`, ou a ETA
      passa a declarar que é piso.
- [x] **Controle:** recomputar as medianas com e sem as linhas de flag e verificar que o
      delta caiu a zero nos stages medidos acima.
- [x] Não mexer na separação `completed`/`skipped` da coluna — é decisão do produtor e está
      fora desta lane.

## Controle A/B (2026-09-01) — e a janela que o enunciado não aplicou

O predicado passou a excluir `output_summary.skipped == true`. Recomputado sobre o
DB de dogfood **com a janela de produção** (`limit_per_stage=20`), o resultado do
código novo é **idêntico**, campo a campo, à mediana calculada à mão sem as linhas
de flag — o delta zerou.

Mas o número do §Medição **não reproduz sob essa janela**. Ele reproduz sem ela:

| stage | erro s/ janela (pop. inteira) | erro **com** a janela de 20 (produção) |
|---|---|---|
| `extract_comprovantes_bens` | −91,0% | *não aparece* — 0 no-op na janela |
| `extract_baseline` | −19,6% | **−0,1%** (1 no-op em 20) |
| `extract_informes_anuais` | −2,5% | *não aparece* |
| `extract_irpf_full` | −0,5% | **0,0%** (1 no-op em 20) |

O conjunto de stages e os valores de `extract_informes_anuais` (75,5k) e
`extract_irpf_full` (332–333k) batem com a tabela do enunciado; o que difere é o
recorte. As 10 linhas de no-op de `extract_informes_anuais` e as 2 de
`extract_comprovantes_bens` são de **maio de 2026** e há muito saíram da janela dos
últimos 20 runs que a produção lê.

## Duas linhas do enunciado envelheceram

1. **"ETA 3,5× otimista para quem está esperando o run terminar"** — o stage do
   headline, `extract_comprovantes_bens`, **não emite ETA**. Os únicos dois
   emissores de `estimated_duration_ms` são `extract_baseline`
   (`pipeline/stages/extract_baseline.py:290`) e
   `extract_irpf_full` (`pipeline/stages/extract_irpf_full.py:101`).
   Nos dois, o erro medido hoje é ≤0,1%.
2. **"o único P2 desta rodada com consequência medida na superfície do usuário"** —
   a consequência medida ficou no stage sem superfície; a superfície ficou sem
   consequência medida. As duas metades não se encontram neste corpus.

**O defeito procede mesmo assim, e o remédio também** — por um motivo que o
enunciado não usou. A ETA só é **lida** no ramo em que o stage executa de verdade:
os quatro early-returns `{"skipped": True}` de cada emissor antecedem a leitura de
`ctx.stage_duration_estimates`. Quando o stage no-opa, nenhuma ETA sai. A amostra
de no-op **nunca pertenceu à população prevista** — o corte é de definição, não de
magnitude.

O regime em que a magnitude importa é o **free tier → chave configurada**: as N
execuções anteriores no-oparam por `No LLM config — free tier`, a janela chega
dominada por milissegundos, e a primeira ETA real subdeclara um stage de ~9 min.
Aí a subdeclaração tende a 100%, não a 72% — e arrasta junto o falso alarme de
travamento, cujo limiar é `2×estimated_duration_ms / items_total` ([[ADR-119]]
§renderização 4).

## Portabilidade do predicado (verificado nos dois dialetos)

É a primeira query com JSON-path do backend. `output_summary["skipped"].as_boolean()`
foi executada contra ambos:

- **SQLite** (dogfood, 1.622 linhas): `JSON_EXTRACT(...)` → `{None: 1585, True: 37}`.
- **Postgres 16** (`docker-compose.test.yml`): `CAST(output_summary ->> 'skipped' AS BOOLEAN)`
  → `[None, None, False, True, True, True]` na fixture; mediana 310.000 (execuções
  reais) em vez de 150.003 (populações misturadas).

Chave ausente e `skipped: false` são preservadas nos dois — só `true` sai.

## O extremo do `PV13-15` é de OUTRO discriminador — e fica aberto

O `PV13-15` (§r13) roteou para esta lane um extremo de **5.766×**: "mediana de
**28 ms** sobre todas as execuções contra **161.449 ms** sobre as reais".
Reproduzido exatamente — e o discriminador **não é a flag desta lane**:

| população de `extract_with_llm` | n | mediana |
|---|---|---|
| todas as execuções | 69 | **28 ms** |
| sem a flag `skipped` (o corte desta lane) | 63 | **25 ms** |
| com `total_processed > 0` | 18 | **161.449 ms** |

O corte desta lane move 28 → 25 ms (−10%), não 28 → 161.449. As 45 linhas que
produzem o 5.766× são **no-op silencioso**: o stage rodou, devolveu
`{"success": true, "processed": [], "total_processed": 0}` em 18–47 ms e **não**
declarou `skipped`. A flag não as alcança, por construção.

**Segue aberto, e sem superfície de usuário hoje.** O no-op silencioso está
confinado a `extract_with_llm` (45 linhas; nenhum outro stage tem uma), e esse
stage não emite `estimated_duration_ms`. Medido nos dois emissores: `extract_baseline`
e `extract_irpf_full` têm **zero** linhas rápidas (<5 s) sem a flag — todo no-op
deles se declara, então o corte desta lane limpa a população inteira que a ETA lê.

O resíduo é latente, não inerte: um emissor futuro com o padrão do
`extract_with_llm` reintroduz a subdeclaração sem tocar em nada desta lane.
Fechar exigiria um predicado de "trabalho feito" que hoje não existe em contrato
(`total_processed` não está em nenhum schema de stage) — escopo de lane própria,
não desta.
