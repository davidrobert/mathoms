---
id: A40.l31
type: lane
title: "Gerador ancora em vez de digitar: correção guiada pelo mecanismo, com o eval como gate de saída"
sprint: A40
plan: PLAN-report-trust
status: planned
priority: P2
branch_slug: a40-l31-gerador-ancora-em-vez-de-digitar
adrs:
  - "[[ADR-341]]"
  - "[[ADR-296]]"
  - "[[ADR-358]]"
depends_on:
  - "[[A40.l30]]"
tags:
  - type/lane
  - sprint/a40
  - status/planned
  - priority/p2
  - area/backend
  - area/pipeline
  - area/llm
---

# A40.l31 — `gerador-ancora-em-vez-de-digitar`

> **`planned` de propósito, e o motivo é a linha de corte de custo.** Esta lane
> gasta (re-eval ~US$ 26, owner-gated) e **não abre antes do item 3 da
> [[A40.l30]]** nomear o mecanismo. Liberação é por lane, sob demanda — ver
> §Predicado do campo `status` no [`_README`](../_README.md).
>
> Co-design `prompt-engineer` 2026-08-03: o corte entre esta lane e a l30 **não é
> medição|mudança** — é **US$ 0 | US$ 26**. Uma lane só ficaria infechável não por
> misturar medir e mudar, mas por **depender de sessão do dono no meio**.

## Problema

O que a [[A40.l30]] mede, esta corrige. O mecanismo, medido sem LLM: o número de
valores monetários que o modelo **vê** no exec context dobrou (9,0 → 18,0 tokens
`R$` no corpo, n=24 fixtures) após #1004, enquanto o conjunto **ancorável** ficou
igual (29 folhas, cap 30) — e a instrução do catálogo manda *"Conceito ausente
daqui → não ancore"*. Digitar o número na prosa é o comportamento que sobra.

Três correções são candidatas e **a l30 §Escopo item 3 decide qual**: curar/ampliar
o catálogo, capar a superfície monetária do corpo, ou reposicionar a regra de
ancoragem face ao corpo dobrado. Escolher antes da medição é chutar.

**Por que não é P0.** O dano que chegava ao usuário — item de conselho apagado, run
derrubado — foi fechado pela [[A40.l16]] e desescalado pela [[ADR-358]]. O que sobra
é **clareza**: número na prosa sem procedência declarada. Pela reformulação do
invariante registrada no incidente (*todo número que o leitor vê tem procedência —
âncora verificada ou estimativa com caveat*), isso é dano de clareza, não de
correção.

## Escopo

1. **A correção que o diagnóstico da l30 indicar** — uma das três acima, não as
   três.
2. **`PROMPT_VERSION` 2.2.0→2.3.0** com entrada de changelog no módulo. Colide com
   o bump planejado pela RV2-01 em [[PLAN-pipeline-review-r2]]: quem chegar
   primeiro leva, o outro rebaseia (registrado na §Handoff da [[A40.l30]]).
3. **Trocar `number_in_prose_median == 0` do eval**
   (`tests/test_parecer_evidencia_llm_eval.py:183`) por taxa com budget declarado —
   é o antipadrão que a [[ADR-358]] §Decisão 2 condenou, sobrevivendo no eval.
   Depende do inventário de campos ampliado (l30 §Escopo item 7): trocar antes
   re-baselina um piso.
4. **Re-ancorar `_DENSITY_FLOOR`** (`:39`, hoje 5, com comentário que se declara
   provisório: *"Piso conservador — re-ancorar na 1ª medição real"*) **por corpus**.
   Nunca igualar o piso do holdout sintético ao número do dogfood.
5. **Re-eval do holdout como gate de saída**, com a entrada da
   [`OWNER-GATED-active`](../../../_MOC/OWNER-GATED-active.md) §2 re-escopada: custo
   alinhado (~US$ 26 na entrada vs ~US$ 29 no comentário do harness) e a
   pré-condição **"fixture com os 3 blocos"** explícita — sem ela o run mede um
   corpus onde o mecanismo não existe.

## Critério de aceite

- Densidade **por item** não piora vs. o baseline declarado de 2.2.0, em janela
  ≥8 runs. **Nunca** contra piso absoluto — o piso é dependente de corpus.
- Prosa monetária dentro do budget declarado, com inventário de campos ampliado
  (≥8) e reportada como **distribuição**, não ponto.
- Cobertura ancorável ≥ baseline da [[A40.l30]].
- `PROMPT_VERSION` 2.2.0→2.3.0 + changelog no módulo; hook `PROMPT_VERSION`
  bumpado verde.
- Re-eval executado **depois** da correção, com a fixture já contendo os 3 blocos.
- Suíte verde: `pytest tests -q` + `pytest backend/tests -q`, da raiz do repo.

## Fora de escopo

- **RV2-10** (fail-open de sub-citação) e **RV2-01** (âncora em `metricas[]`)
  seguem em [[PLAN-pipeline-review-r2]], com dono próprio. Esta lane não os absorve
  — abriria duas fontes de verdade no mesmo arquivo, que é a razão declarada da
  §Fora do sprint para RV3-19.
- **Reescrever a persona.** O co-design mediu que as instruções do gerador não
  mudaram em #1004 (14 linhas, só a regra de recovery); tratar isto como defeito de
  persona foi a premissa errada que o co-design corrigiu.
