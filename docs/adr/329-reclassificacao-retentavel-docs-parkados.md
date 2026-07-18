---
id: ADR-329
type: adr
title: "Reclassificação re-tentável de documentos parkados por skip transitório (missing_api_key) no run premium"
status: Proposto
date: "2026-07-12"
relates_to:
  - "[[ADR-081]]"
tags:
  - type/adr
  - status/proposto
  - area/backend
  - area/pipeline
---

# ADR-329 — Reclassificação re-tentável de docs parkados

> Item **C8** do plano PLAN-dogfood-report-fix. Achado DE-05 da revisão dogfood.
> Emenda semântica ao padrão de classificação [[ADR-081]].

## Contexto

10 documentos (7% do corpus dogfood) estão presos em `needs_review` com
`doc_type='other'`, `classification_confidence=0.0` e
`classification_meta.llm_skipped_reason='missing_api_key'`, `reclassified_at=2026-05-28`
(chave LLM ausente na época). O run atual — com chave presente e 6 chamadas LLM
bem-sucedidas — **não re-classificou** os docs parkados. Um skip **transitório**
(chave ausente) ficou permanente na prática: o documento é excluído
silenciosamente da análise para sempre.

## Decisão

Tornar skips transitórios **re-tentáveis**, distinguindo-os dos permanentes:

1. **`RETRIABLE_SKIP_REASONS`** (frozenset) em
   `document_classification.py`, ao lado de `_TRANSIENT_ERROR_NAMES` — inclui
   `missing_api_key` (transitório) e exclui razões terminais (conteúdo
   genuinamente ambíguo).
2. **Hook de retry no início do run premium** (`pipeline_task.py`, após setup do
   contexto e antes do loop de stages), gated por `tier=='premium'` **e**
   `ANTHROPIC_API_KEY` presente: re-classifica docs `needs_review` cujo
   `skip_reason` é retriável, roteando os re-classificados para o corpus antes
   de E1/E2. Função-alvo dedicada (não `reclassify` full-workspace).
3. **OCR determinístico** como fallback secundário para `content_regex_empty`
   (imagem/PDF sem camada de texto) antes de desistir.
4. **Superficar `needs_review` por motivo** no relatório (contrato E5 ganha
   `documentos_pendentes`, com flag in-window) — bump aditivo de schema E5.

## Alternativas consideradas

- **Re-classificar tudo a cada run.** Rejeitada: custo LLM desnecessário; só
  docs parkados por motivo transitório precisam de retry.
- **Retry manual via console.** Rejeitada como default: o skip transitório deve
  auto-resolver quando a pré-condição volta, sem ação humana.

## Consequências

- Docs parkados por chave ausente re-entram no corpus no primeiro run premium
  com chave — sem perda silenciosa.
- Skip permanente (ambiguidade real) **não** re-tenta (evita loop de custo).
- `retry_count`/backoff evita retry infinito sobre motivo que persiste.

## Critério de aceite (4 lentes)

- **Completude:** todos os skips transitórios re-tentáveis; 3 formatos cobertos; gate premium+chave.
- **Corretude:** doc parkado re-classifica e entra no corpus do mesmo run; skip permanente não re-tenta.
- **Consistência:** contagem de pendentes no relatório == UI de documentos.
- **Precisão:** schema strict no CI para `documentos_pendentes` + métrica por run (re-tentados/re-classificados/parkados).
