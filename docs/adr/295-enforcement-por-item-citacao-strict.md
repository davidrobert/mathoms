---
id: ADR-295
type: adr
title: "Enforcement por-item da citação verificada no modo strict (parecer E6)"
status: Proposto
phase: "A26 · parecer reliability"
date: "2026-06-17"
relates_to:
  - "[[ADR-279]]"
  - "[[ADR-292]]"
  - "[[ADR-081]]"
  - "[[ADR-202]]"
supersedes: []
superseded_by: []
aliases: ["ADR 295", "enforcement por-item citação", "strict per-item parecer"]
tags:
  - type/adr
  - status/proposto
  - area/llm
  - area/pipeline
  - phase/a26
---

# ADR-295 — Enforcement por-item da citação verificada no modo strict

**Status:** Proposto (A26 · parecer reliability) • **Data:** 2026-06-17 •
**Relaciona** [[ADR-279]] (citação verificada E5→E6), [[ADR-292]] (coerção de
path), [[ADR-081]] (regex→LLM→needs_review), [[ADR-202]] (schema do parecer).
Co-design `prompt-engineer` + `senior-cto` 2026-06-17 (lane [[A26.l8]]).

## Contexto

A [[A26.l2]] vai flipar `evidencia_verification_mode: warn→strict`. A decisão
cravada do co-design da sprint era: em `strict`, **1 violação de citação →
parecer INTEIRO vira `needs_review`** (per-parecer). Eval golden real no `main`
1.7.0 + [[ADR-292]] (50 runs gate holdout, sonnet-4-6, 2026-06-17) trouxe
evidência nova que torna esse gate inatingível por prompt:

| Métrica | valor |
|---|---|
| conformidade **por citação** | **96,2%** (≥95% ✅) |
| per-parecer UB IC95 (hard) | **49,9%** (gate <5% ❌) |
| `whitelist_miss` / `resolve_null` | **0** (catálogo l1 + ADR-292 zeraram) |
| resíduo | **100% `value_mismatch`** (path válido, número errado), determinístico |

**Aritmética decisiva:** com ~10-15 citações/parecer, conformidade por citação
de 96,2% ⟹ `1 − 0,962¹⁵ ≈ 36%` de pareceres com ≥1 falha. Para per-parecer
<5% seria preciso **~99,6% por citação** — barra que o LLM não cruza escrevendo
número em prosa à mão. A decisão "per-parecer" foi tomada **antes** desta
evidência empírica; é o gatilho de reabertura legítima (senior-cto decide e fecha,
anti-loop).

**Auto-correção pós-hoc foi considerada e REJEITADA** (co-design): reescrever o
número da prosa pela folha do path citado fecharia o gate por construção, mas
**troca um erro detectável por um indetectável** — se o LLM citou o path errado,
publicaríamos um número confiantemente errado e "verde", apagando o sinal
`value_mismatch → needs_review`. Em produto de planejamento financeiro o dano é
assimétrico (falso-positivo silencioso > falso-negativo barulhento). Guardrail de
magnitude não separa "transcrição de cópia" de "pareamento errado". E violaria
[[ADR-279]] §E (verificador viraria gerador) — mesmo princípio que [[ADR-292]]
cravou ao **rejeitar truncar prosa silenciosamente**.

## Decisão

**No modo `strict`, a unidade de enforcement é o ITEM, não o parecer.**

1. **Citação que falha (`value_mismatch`/`whitelist_miss`/`resolve_null`) derruba
   AQUELE risco/sugestão** — o item sai do parecer publicado; os demais seguem. O
   parecer só vira `needs_review` se o item descartado for **severidade alta**
   (silenciar um risco crítico é tão ruim quanto emitir número errado). `warn`
   permanece observação pura. `missing_path` continua cobertura (fail-open,
   [[ADR-292]] §4), nunca derruba item.

2. **Novo outcome `item_dropped`** em `EvidenciaVerification.entries` + contador no
   `summary()`, distinto de `verified`/`failed`. Sem isso o descarte por-item vira
   buraco negro de telemetria (densidade cai sem alarme). PII-safe (só path +
   camada, como hoje).

3. **Tolerância de abreviação no `_token_matches`** (bucket "abreviação de
   boundary": `R$ 5,2 mi` vs folha `5.180.000` — o número já está certo, a banda
   meia-casa é estreita no boundary). Banda **proporcional à casa abreviada**,
   nunca fixa. Ampliar o que o verificador aceita como correto **emenda
   [[ADR-279]] §E** (declarada aqui).

4. **Prompt: few-shot negativo anti-derivação** (bucket "deriva/soma baldes" —
   não copiar a folha) para reduzir a incidência. Resíduo que sobra é
   `needs_review`/`item_dropped` legítimo.

**Gate per-parecer <5% permanece como KR de saúde** (mede a qualidade da geração),
mas a **ação de enforcement** é per-item. Os dois papéis são distintos: a métrica
não-conformidade continua medida; o que muda é o que o strict faz com ela.

## Consequências

- **Gate fecha sem falsificar:** o parecer publicado não tem citação não-verificada
  (itens ruins saíram), e nenhum número foi fabricado — o sinal é preservado
  (`item_dropped` é auditável, não silencioso).
- **Custo de produto:** parecer afetado perde 1 risco/sugestão (densidade cai
  marginalmente). Mitigado pelo guardrail de severidade (item alto → needs_review).
- **`A26.l2` consome esta granularidade:** o flip strict referencia esta ADR;
  `_check_evidencia` deixa de retornar `violations[0] → parecer inteiro`.
- **Telemetria de drift:** razão `item_dropped / total_itens` subindo = modelo
  piorando na citação — sinal que per-parecer escondia.

## Fora de escopo

- **Auto-correção de número:** rejeitada acima; não reentra sem nova evidência +
  emenda explícita ao contrato.
- **Magnitude/banda como gate de correção:** rejeitada (armadilha de pareamento).
- **Re-eval golden owner-gated** valida per-parecer <5% + temp=0 0 violações —
  critério de aceite da [[A26.l8]], não desta ADR.
