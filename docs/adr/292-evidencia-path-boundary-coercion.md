---
id: ADR-292
type: adr
title: "evidencia_path/field_path inválido → None no boundary do LLM (anti reask storm do parecer)"
status: Decidido
phase: "A26 · parecer reliability"
date: "2026-06-16"
relates_to:
  - "[[ADR-279]]"
  - "[[ADR-202]]"
  - "[[ADR-270]]"
  - "[[ADR-203]]"
  - "[[ADR-289]]"
  - "[[ADR-294]]"
supersedes: []
superseded_by: []
aliases: ["ADR 292", "evidencia_path coercion", "parecer reask storm"]
tags:
  - type/adr
  - status/decidido
  - area/llm
  - area/pipeline
  - phase/a26
---

# ADR-292 — `evidencia_path`/`field_path` inválido → `None` no boundary do LLM

**Status:** Decidido (A26 · parecer reliability) • **Data:** 2026-06-16 •
**Relaciona** [[ADR-279]] (citação verificada E5→E6), [[ADR-202]] (schema do
parecer §D6), [[ADR-270]] (timeout/retry LLM), [[ADR-203]] (drill-down),
[[ADR-289]] (catálogo de modelos).

## Contexto

Incidente de produção (workspace `5@5.com`, 2026-06-16): o stage
`review_finances_holistic` levava **243–256s** e falhava intermitentemente
(`needs_review`). Diagnóstico com dados de `planner_review_metadata`:

A migração `claude-sonnet-4-20250514` → `claude-sonnet-4-6` (06-16) mudou o
perfil de geração: `tokens_out` saltou de ~4k para **~16,5k (cravado no
`max_tokens=16384`)** e a latência de ~60s para ~250s. O erro real da run que
falhou:

```
Output validation failed after 4 attempts: 13 validation errors
- riscos.N.evidencia_path: String should match pattern '^\$\.[A-Za-z_]...'
  input_value="$.alocacao_por_classe[?(@.classe=='Caixa')].valor"
  input_value="$.ativos[?(@.descricao=~'.*Exemplo.*')].valor"
- diagnostico_geral: String should have at most 500 characters
```

O modelo novo emite **JSONPath com filtros** (`[?(@.x=='y')]`, `=~`, `..`) em
`evidencia_path` para citar elementos de **lista** (alocação por classe, ativo
individual) — que o catálogo de citação v1 ([[ADR-279]] §E, A26.l1) não cobre
("strings/listas ficam fora do v1"). O `_JSONPATH_RE` é um subset deliberado
**sem filtros** (verificador e schema compartilham a mesma gramática). O
`pattern=` no campo Pydantic transformava cada filtro num **hard-fail de
schema** → reask do Instructor (`max_retries=2`) + retry externo → até **4
gerações completas de ~16k tokens** ≈ 243–256s, terminando em `needs_review`.

A emenda [[ADR-270]] (timeout 120→240s) foi band-aid: subiu o teto sem atacar
por que as gerações se multiplicavam.

## Decisão

**Coerção no boundary em vez de hard-fail** — mesmo padrão de
`_normalize_confianca` (criado após "4 retries falhavam" em 2026-05-18).

1. **`evidencia_path` (Risco/Sugestao) + `field_path` (CampoFaltante):**
   `BeforeValidator` `_coerce_jsonpath_or_none` — path fora do subset (ou >255
   chars) vira `None`, não raise. Output valida na **1ª geração**;
   `verify_evidencia` registra `missing_path` (não-fatal em `warn`, modo ativo).
   Log PII-safe da categoria de drift (`filter`/`regex_match`/`recursive_descent`),
   **nunca o valor** — um filtro carrega nome próprio (LGPD). `field_path` passa
   a `Optional` (era required); a regra 3 do prompt manda registrar paths
   não-whitelistados ali — i.e. exatamente os que falham o regex.

2. **Caps de prosa elevados** (sign-off `product-designer`; renderer
   `SParecer/` é flow-based, sem altura fixa/`line-clamp`), por função
   tipográfica, não multiplicador único: `diagnostico_geral` 500→750,
   `Risco.descricao` 500→650, `PontoForte.descricao` 400→520, `Sugestao.acao`
   280→**340** (título de card — folga mínima), `impacto_qualitativo` 320→420,
   `evidencia` 300→390, `caveat` 240→300, `nota.conteudo` 600→780. JSON Schema
   espelha. Truncar silenciosamente foi **rejeitado** (mutila texto user-facing
   e mascara drift de verbosidade).

3. **Prompt:** regra de gramática anti-filtro explícita ("se só alcançável por
   filtro, omita `evidencia_path` — não invente"). `PROMPT_VERSION` 1.6.0→1.7.0.
   `EVIDENCIA_VERIFICATION_VERSION` 1→2 (output persistido muda → invalida cache).

4. **Métrica do eval (`test_parecer_evidencia_llm_eval.py`):** `violation` exclui
   `missing_path` — passa a contar só `value_mismatch + whitelist_miss +
   resolve_null` (citação que resolve **errado**). `missing_path` é **cobertura**
   reportada à parte. Sem isso, a coerção fazia `missing_path` subir
   mecanicamente (antes morria em reask, nunca chegava ao verificador) e o gate
   de 5% do flip strict (A26.l2) reprovaria por *visibilidade*, não regressão.

## Consequências

- **Reliability:** path-filtro deixa de gerar reask — geração única (~65s) no
  lugar de 4× (~250s). Em `warn` (ativo) o end-state é idêntico: `missing_path`
  já era não-fatal. Resolve o incidente sem tocar `max_tokens` (o 16k cravado era
  contaminado pelo reask; pós-fix cabe abaixo).
- **Citação:** perde-se a *ancoragem por path* de valores de lista — é gap de
  **cobertura de catálogo**, não de confiabilidade. A verificação de valor R$ na
  prosa contra o E5 ([[ADR-279]]) permanece intacta.
- **Custo:** invalidação dos caches do parecer pré-coerção (esperado).

## Fora de escopo (A26.l2)

- **Semântica de `missing_path` em `strict`:** hoje dispara `needs_review`
  (`test_prosa_monetaria_sem_path_missing_path`). Com a coerção roteando
  filtros para `missing_path`, o flip strict precisa decidir se `missing_path`
  é fail-open (recomendação data-engineer) — **não alterado aqui** (modo strict
  inativo; é decisão da lane de flip). Runtime `_check_evidencia` permanece.
- **Extensão do catálogo a listas** via paths indexados `[idx].subkey` (match
  escalar único; nunca `[*]` agrupado, que fragiliza o `any()` do verificador).
  É o follow-up que fecha a raiz: o modelo para de querer filtro porque ganha
  path escalar legítimo.
- **Re-eval golden owner-gated contra `sonnet-4-6`** (KR1 A26) — o processo que
  deixou um modelo novo chegar a prod sem eval é o bug de fundo.
