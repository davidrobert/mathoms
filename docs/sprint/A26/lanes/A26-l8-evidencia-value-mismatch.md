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

## Resultado do eval no 1.8.0 (strict) + classificação (2026-06-18)

Eval real holdout (50 gate strict + 10 temp=0, sonnet-4-6, US$ 11,63):

| Métrica | 1.8.0 | **1.9.0** (pós regra de pareamento, #666) | Alvo (gate redefinido) |
|---|---|---|---|
| **needs_review (gate strict)** | 11/50 · UB 35,2% | **3/50 = 6% · UB 16,2%** | ≤15% 🟢 (ponto) / UB 🟡 |
| items_dropped (baixo/médio) | 4/50 | 5/50 | — |
| raw hard (pré-enforcement) | 15/50 · UB 43,8% | **UB 28,5%** | (1.7.0 era 49,9%) |
| conformidade por citação | 94,7% | **98,6%** | ≥95% 🟢 |
| diag temp=0 needs_review | 2/10 | 3/10 | 0 🔴 (resíduo determinístico) |

**Por que não fecha:** ~73% das falhas hard caem em itens de **severidade alta** →
`needs_review` (correto; não silenciamos risco crítico). O enforcement per-item só
dropa baixo/médio (4/50). Gate per-parecer <5% não atingido.

**Classificação do value_mismatch (40 gerações warn, captura do triple):**
`wrong_pairing` **~87%** (número REAL do E5, mas atrelado ao path errado — ex.:
escreve a receita R$ 720k citando `previdencia_pgbl.contribuicao_anual`),
`hallucination` ~13% (inflado por cap de 50 folhas), **`rounding/abbrev` = 0**.

**Implicações cravadas:**
- Ampliar tolerância de abreviação no `_token_matches` (escopo §3) **não ajudaria**
  (0 casos). Removido do escopo.
- **Auto-correção (valor OU path) confirmada perigosa:** wrong_pairing = a *frase*
  atribui número real ao *conceito errado*; corrigir publica afirmação enganosa.
  needs_review é o destino correto. [[ADR-295]] validada empiricamente.
- A raiz é **capacidade do LLM** de manter número↔conceito coerente; o catálogo
  `path→valor` já existe e mesmo assim mispareia ~22%/parecer.

**Re-eval no 1.9.0 (2026-06-19, regra "par número↔path é UMA escolha"):** o caminho 3
(iteração de prompt) foi a iteração **mais eficaz** — needs_review **22% → 6%**,
conformidade **94,7% → 98,6%**, raw hard UB **43,8% → 28,5%**. Contra o gate redefinido
(budget ≤15%): **ponto estimado 6% passa; UB IC95 16,2% marginal** (largura de n=50, 3
eventos — aperta com mais volume real). temp=0 mantém 3/10 → resíduo determinístico que
só a [[A26.l9]] elimina. **Conclusão:** o flip ([[A26.l2]]) fica **viável no critério
redefinido** (segurança ✅ + budget ~6%); a l9 rebaixa de "necessária p/ o flip" para
"polir o resíduo de 6%→0" (A27).

**Caminhos abertos (decisão de produto/owner):**
1. **Determinístico (recomendado p/ matar value_mismatch por construção):** parar de
   deixar o LLM *escrever* o número — emitir `(claim_text, evidencia_path)` e
   **renderizar o valor da folha server-side** (token tipo `MonetaryValue` a partir
   do path). value_mismatch → 0 estrutural (o número exibido É o da folha). Resíduo
   vira só "path/conceito errado", menor. Mudança de schema+prompt+renderer (co-design
   `senior-cto` + `product-designer`). Aberto como [[A26.l9]] (A27/Onda 6, [[ADR-296]]).
2. **Redefinir o gate (l2):** a propriedade que protege o usuário — "zero citação
   errada publicada" — JÁ é atingida pelo enforcement. Trocar o gate de
   "needs_review per-parecer <5%" para "0 falso publicado + needs_review tolerável".
3. Iteração de prompt (pareamento número↔path) + modelo/temp — payoff incerto.

## Owner

Agente da lane; co-design `prompt-engineer` (eval + few-shot anti-derivação) +
`senior-cto` (granularidade per-item / [[ADR-295]]) — feito 2026-06-17. Eval +
classificação 2026-06-18.
