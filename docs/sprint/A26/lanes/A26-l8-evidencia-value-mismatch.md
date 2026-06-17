---
id: A26.l8
type: lane
title: "value_mismatch residual: enforcement per-item no strict (path válido, número errado)"
sprint: A26
plan: PLAN-data-lineage
status: planned
priority: P1
branch_slug: evidencia-value-mismatch
adrs:
  - "[[ADR-279]]"
  - "[[ADR-292]]"
  - "[[ADR-295]]"
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
> `value_mismatch` (path válido, número errado). **Co-design `prompt-engineer` +
> `senior-cto` 2026-06-17 cravou a abordagem** (ver [[ADR-295]]): **auto-correção
> de número foi REJEITADA** (trocaria erro detectável por erro confiante e
> silencioso num produto financeiro); a alavanca é **enforcement per-item no
> strict** + tolerância de abreviação + few-shot. **Bloqueia o flip da [[A26.l2]]**.

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

Viabilizar o gate per-parecer <5% **sem falsificar nem relaxar** o que o
verificador considera correto — mudando a unidade de enforcement (per-item) e
corrigindo o boundary de abreviação, conforme [[ADR-295]].

## Escopo (ordem de ataque — co-design 2026-06-17)

1. **Instrumentar o triple** `(número citado ↔ folha resolvida ↔ path)` no
   harness/telemetria — hoje só há contagem por camada. Classificar os ~19 em:
   (a) **abreviação de boundary** (`R$ 5,2 mi` vs `5.180.000` — número certo, banda
   estreita); (b) **derivação/arredondamento** (LLM soma baldes); (c) **pareamento
   errado** (cita path A, número de B). Decide a calibração do resto.
2. **Enforcement per-item no strict ([[ADR-295]] — alavanca do gate):**
   `_check_evidencia` deixa de derrubar o parecer inteiro (`violations[0]`); a
   citação que falha derruba **aquele item** (risco/sugestão sai), demais seguem.
   `needs_review` só se o item descartado for **severidade alta**. Novo outcome
   `item_dropped` em `entries` + contador no `summary()` (auditável, PII-safe).
3. **Tolerância de abreviação no `_token_matches`** (bucket a): banda **proporcional
   à casa abreviada**, nunca fixa. Muda o que o verificador aceita → **emenda
   [[ADR-279]] §E** (declarada na [[ADR-295]] §3).
4. **Few-shot negativo anti-derivação** no prompt (bucket b) — não somar baldes/
   copiar a folha. Bump `PROMPT_VERSION` se tocar o system prompt.
5. **Auto-correção de número: FORA** ([[ADR-295]] — rejeitada; trocaria erro
   detectável por confiante-e-silencioso).

## Critério de aceite

- Os ~19 `value_mismatch` classificados (a/b/c) com o triple registrado no harness —
  decisão por bucket no corpo do PR.
- Re-eval holdout (owner-gated): per-parecer UB IC95 **<5%**, 5 runs/fixture, temp de
  produção; braço temp=0 **0 violações** (resíduo determinístico à raiz).
- Conformidade por citação **não regride** (≥96%); densidade de citação **não cai**
  (sem mascarar via sub-citação nem via descarte excessivo de itens).
- Teste de granularidade per-item em `tests/test_parecer_evidencia_path.py`: 1 item
  ofensor descartado → parecer publica os demais; item severidade alta descartado →
  `needs_review`. Teste adversarial (pareamento errado de magnitudes próximas →
  enforcement remove o item, não falsifica) verde.
- [[ADR-295]] `Proposto`→`Decidido (A26)` no merge; emenda [[ADR-279]] §E se a banda
  de abreviação mudar o aceite do verificador.

## Notas

- **Granularidade per-item** reabre a decisão cravada "per-parecer" da sprint — feito
  via [[ADR-295]] (senior-cto decide e fecha, evidência empírica do eval). O gate
  per-parecer <5% permanece como **KR de saúde**; o que muda é a **ação** do strict.
- **Débito do harness:** o eval roda sequencial (~1,7h, sujeito a kill). O padrão
  paralelo + persistência incremental foi provado em `_scratch/run_parecer_eval_parallel.py`
  (6 workers, ~13 min); promovê-lo ao harness committed é melhoria desta lane ou da [[A26.l6]].

## Owner

Agente da lane; co-design `prompt-engineer` (eval + few-shot anti-derivação) +
`senior-cto` (granularidade per-item / [[ADR-295]]) — feito 2026-06-17.
