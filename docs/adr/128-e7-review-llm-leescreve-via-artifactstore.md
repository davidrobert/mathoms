---
id: ADR-128
type: adr
title: "E7-review-llm lê/escreve via `ArtifactStore`"
status: Decidido
phase: "A6-cleanup"
date: "2026-04-24"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 128"]
tags:
  - type/adr
  - status/decidido
size_lines: 40
---

# ADR-128 — E7-review-llm lê/escreve via `ArtifactStore`

**Status:** Decidido (A6-cleanup) • **Data:** 2026-04-24

**Contexto:** Após ADR-083 (ArtifactStore) e o cutover
`MATHOMS_USE_DB_ARTIFACTS=True`, o stage `E7-review-llm`
(`pipeline/stages/e7_review_llm.py`) continuava como caminho legado:
lia `analise_financeira-5_analysis.json` via `Path.exists/read_text`,
fazia `ctx.e7_dir.glob("*crossval*")` e gravava `review_llm-7_review.json`
com `Path.write_text`. Isso quebrava a invariante de `pipeline/**`
(stateless, testável sem disco) e impedia que o stage rodasse em
Celery worker com DB-backed store.

**Decisão:** Stage passa a usar `ctx.get_artifact_store()`:

- `store.read("E5", "analise_financeira")` para o input principal.
- `store.read("E7-crossval", key)` via `list_keys` — política: primeira
  chave alfabética (hoje o writer de E7-crossval ainda grava template
  em disco; quando migrar, a primeira chave passa a aparecer automaticamente).
  Fallback `"{}"` preserva o comportamento do glob legado.
- `store.write("E7-review", "review_llm", ...)` para o output. Mapping
  `E7-review` → `E7_review/review_llm-7_review.json` já existe em
  `pipeline/artifact_store.py` (ADR-083); filename resultante é idêntico
  ao legado.

Os helpers `_load_json_file` e `_load_e5_compact` foram refatorados para
receber `dict | None` em vez de `Path` — I/O sai da camada de domínio.

**Consequências:**
- ✅ Stage agora é stateless; testável com `InMemoryArtifactStore` sem
  tocar disco (teste `test_llm_stages_e7.py` migrado).
- ✅ Compatível com Celery worker rodando `DBArtifactStore`.
- ⚠️ Leitura de E7-crossval depende de o writer migrar também —
  enquanto não migrar, fallback `"{}"` mantém o comportamento prévio
  (o glob `*crossval*` nunca casou com `e7_review_template.json`, então
  efetivamente o payload sempre foi vazio em prod; nada regrede).
- ❌ `MaterializationBridge` não é necessário aqui — E7-review-llm não
  é consumido por script legado; só pelo pipeline novo.
