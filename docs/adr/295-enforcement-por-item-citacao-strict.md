---
id: ADR-295
type: adr
title: "Enforcement por-item da citação verificada no modo strict (parecer E6)"
status: Decidido
phase: "A26 · parecer reliability (A26.l8)"
date: "2026-06-17"
relates_to:
  - "[[ADR-279]]"
  - "[[ADR-292]]"
  - "[[ADR-081]]"
  - "[[ADR-202]]"
supersedes: []
superseded_by: []
amended_at: ["2026-08-24"]
aliases: ["ADR 295", "enforcement por-item citação", "strict per-item parecer"]
tags:
  - type/adr
  - status/decidido
  - area/llm
  - area/pipeline
  - phase/a26
---

# ADR-295 — Enforcement por-item da citação verificada no modo strict

> **Correção (2026-08-24):** a camada `value_mismatch` da §Decisão 1 foi
> substituída por `pairing_mismatch` ([[ADR-296]]), e o desfecho de severidade
> alta é a **retenção do parecer inteiro**, não a remoção do item ([[ADR-366]]).
> Ver §"Correção — camadas e desfecho de severidade alta (2026-08-24)".

**Status:** Decidido (A26.l8 — impl. em `parecer_strict_enforcement.py`, #666;
validada empiricamente no eval 1.8.0→1.9.0) • **Data:** 2026-06-17 •
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

## Correção — camadas e desfecho de severidade alta (2026-08-24)

Auditoria de vault r10 (F04 · [[ADR-302]]). Duas afirmações da §Decisão 1
deixaram de valer; nenhuma delas reabre a decisão desta ADR — ambas foram
tomadas por ADRs posteriores que esta nunca registrou.

**1. A camada mudou de nome e de natureza.** A §Decisão 1 lista
`value_mismatch` entre as camadas que derrubam um item. Fonte de verdade —
`backend/app/services/parecer_strict_enforcement.py:19-24`:

```python
# ADR-296: pairing_mismatch (rotulo ↔ root incoerente) substitui value_mismatch.
_HARD_LAYERS = frozenset({"whitelist_miss", "resolve_null", "pairing_mismatch"})
```

`value_mismatch` está **zerado por construção** — "prosa não tem R$"
(`parecer_evidencia.py:88-89`). Testar enforcement contra ela produz verde que
não exercita nada.

**2. O desfecho de severidade alta é retenção total.** A §Decisão 1 diz que o
item sai e "os demais seguem". O real é `_withhold_all`
(`parecer_strict_enforcement.py:139-148`): o parecer **inteiro** é retido,
`dropped` fica vazio de propósito e o stage devolve `success: False` — como a
[[ADR-366]] §desfecho já descrevia.

**3. Dois símbolos citados nunca existiram:** `_token_matches` (§Decisão,
tolerância de abreviação) e o outcome `item_dropped` em
`EvidenciaVerification.entries`. `rg -l "_token_matches|item_dropped" -g '!docs/**'`
retorna zero; o implementado é `items_dropped` + `dropped_items` no bloco de
retenção (`parecer_evidencia.py:140-147`), fora de `entries`.
