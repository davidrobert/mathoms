---
id: A26.l8
type: lane
title: "value_mismatch residual: path válido, número errado (auto-correção pós-hoc)"
sprint: A26
plan: PLAN-data-lineage
status: planned
priority: P1
branch_slug: evidencia-value-mismatch
adrs:
  - "[[ADR-279]]"
  - "[[ADR-292]]"
depends_on:
  - "[[A26.l1]]"
parallel_with:
  - "[[A26.l6]]"
  - "[[A26.l7]]"
tags:
  - type/lane
  - sprint/a26
  - status/planned
  - priority/p1
  - area/data-lineage
  - area/llm
---

# A26.l8 — `evidencia-value-mismatch` (Onda 6 · cobertura de citação · Regime A)

> **Plano:** [[PLAN-data-lineage]] §Onda 6. **Sem gate de tráfego** (Regime A —
> código + eval). Fecha o **resíduo hard** que sobra depois do catálogo ([[A26.l1]]),
> da coerção de path ([[ADR-292]]) e da cobertura de listas ([[A26.l7]]):
> `value_mismatch` (path válido, número errado). Co-design `prompt-engineer` +
> `data-engineer` a fazer ao planejar. **Bloqueia o flip da [[A26.l2]]** enquanto o
> gate per-parecer estiver acima de 5%.

## Evidência (eval golden 1.7.0 + ADR-292, 2026-06-17)

Eval real (`tests/test_parecer_evidencia_llm_eval.py`, 50 runs gate holdout + 10
temp=0), sonnet-4-6:

| Métrica | 1.6.0 | **1.7.0** | Alvo |
|---|---|---|---|
| per-parecer UB IC95 (hard) | 59,6% | **49,9%** | <5% 🔴 |
| conformidade por citação | 93,3% | **96,2%** | ≥95% 🟢 |
| diag temp=0 violações | 6/10 | **3/10** | 0 🔴 |
| falhas hard por camada | vm=30, wl=6 | **value_mismatch=19, whitelist=0, resolve_null=0** | |

**Diagnóstico:** o catálogo ([[A26.l1]]) + [[ADR-292]] **zeraram `whitelist_miss` e
`resolve_null`**; a conformidade por **citação** cruzou 95%. Mas o gate é
**per-parecer** ([[A26.l2]]: 1 violação → parecer inteiro vira `needs_review`), e
com ~10-15 citações/parecer × 96,2% ≈ **36% de pareceres com ≥1 falha**. Para
per-parecer <5% seria preciso **~99,6% por citação** — barra que o LLM não cruza
escrevendo número em prosa à mão. O resíduo é **100% `value_mismatch`** (path
válido, número da prosa ≠ folha) e é **determinístico** (falha em temp=0).

## Objetivo

Derrubar `value_mismatch` ao nível que viabilize o gate per-parecer <5% — sem
relaxar o que o verificador considera correto.

## Escopo

1. **Instrumentar o triple** `(número citado na prosa ↔ valor da folha resolvida ↔
   path)` no harness/telemetria — hoje o eval só guarda contagem por camada, não o
   par que mismatou. Classificar os ~19 casos em: (a) **abreviação legítima**
   (`R$ 5,2 mi` vs folha `5.180.000` — meia-casa do verificador falha no boundary);
   (b) **derivação/arredondamento** (LLM soma/ratio/arredonda em vez de copiar);
   (c) **pareamento errado** (cita path A, escreve número de B).
2. **Auto-correção pós-hoc (alavanca principal — avaliar primeiro):** como o valor
   canônico está na folha citada, reconciliar/substituir o token R$ da prosa pelo
   valor formatado da folha **antes** do verify → `value_mismatch → 0 por
   construção`. Decisão de design (co-design `prompt-engineer` + `senior-cto`): é
   correção silenciosa segura (o path é a fonte de verdade) ou precisa de guardrail
   contra trocar o número numa frase onde ele muda o sentido? Provável: corrigir só
   quando o path resolve a 1 folha escalar e a frase referencia aquele path.
3. **Tolerância de abreviação no verificador** (se (a) for material): ampliar a
   meia-casa de `_token_matches` para casar `R$ X,Y mi/mil` com a folha exata sem
   abrir porta a alucinação (banda proporcional à magnitude abreviada, não fixa).
4. **Prompt** (se (b)/(c) forem materiais): reforço de cópia verbatim do catálogo já
   existe (regra 11, 1.6.0); medir se um few-shot negativo (não derivar/somar) ajuda.

## Critério de aceite

- Os ~19 `value_mismatch` classificados (a/b/c) com o triple registrado — decisão de
  abordagem no PR.
- Re-eval holdout (owner-gated): per-parecer UB IC95 **<5%**, 5 runs/fixture, temp de
  produção; braço temp=0 **0 violações** (o resíduo determinístico foi à raiz).
- Conformidade por citação **não regride** (≥96%); densidade de citação **não cai**
  (sem mascarar via sub-citação).
- `tests/test_parecer_evidencia_path.py` verde (verificador determinístico).
- Sem ADR nova — conforma [[ADR-279]] §E (a auto-correção usa a folha como fonte de
  verdade, não relaxa o contrato). Se a auto-correção mudar o contrato de citação,
  abrir emenda à [[ADR-279]] **antes** do PR.

## Notas

- **Tensão estratégica a decidir com `senior-cto`:** se per-parecer <5% for inatingível
  por prompt/verificador, a alternativa é a auto-correção (item 2) **ou** repensar a
  granularidade do strict ([[A26.l2]]: rejeitar só o item ofensor, não o parecer
  inteiro). A granularidade per-parecer é decisão cravada do co-design da sprint —
  **não reabrir sem escalar**; a auto-correção é o caminho que respeita o gate atual.
- **Débito do harness:** o eval roda sequencial (~1,7h, sujeito a kill). O padrão
  paralelo + persistência incremental foi provado em `_scratch/run_parecer_eval_parallel.py`
  (6 workers, ~13 min); promovê-lo ao harness committed é melhoria desta lane ou da [[A26.l6]].

## Owner

Agente da lane; co-design `prompt-engineer` (auto-correção + eval) + `senior-cto`
(se tocar contrato/granularidade do gate).
