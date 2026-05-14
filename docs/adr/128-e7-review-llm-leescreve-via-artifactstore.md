---
id: ADR-128
type: adr
title: "E7-review-llm lê/escreve via `ArtifactStore`"
status: Decidido
phase: "A6-cleanup (superseded em A12.X — deprecation Ato 6 do PLANNER_REVIEW)"
date: "2026-04-24"
relates_to: []
supersedes: []
superseded_by: ["[[ADR-199]]"]
aliases: ["ADR 128"]
tags:
  - area/llm
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 48
---

# ADR-128 — E7-review-llm lê/escreve via `ArtifactStore`

**Status:** Decidido (A6-cleanup) • **Data:** 2026-04-24

**Cutover 2026-05-14 (Ato 6 do plano [`PLANNER_REVIEW`](../plan/PLANNER_REVIEW/_README.md)):**
Stage `review_finances` (E7-review) marcado `is_deprecated=True` no
`STAGE_REGISTRY` (`pipeline/stage_spec.py`). `pipeline/stages/review_finances.py`
emite `DeprecationWarning` ao executar. Supersedido por
[[ADR-199]] (`parecer_planejador` / `review_finances_holistic`). Sprint
A12.X (TBD) remove código + migration de cleanup de artifacts E7-review
ainda armazenados — pareceres antigos podem ser conservados para
auditoria via política de retenção (dado-engineer decide na sprint do
remove).

**Nota 2026-05-13:** Esta ADR será superseded por [[ADR-199]] (parecer
planejador) durante execução do plano [`PLANNER_REVIEW`](../plan/PLANNER_REVIEW/_README.md).
Artifact `("E7-review", "review_llm")` deixará de ser gerado quando
`parecer_planejador` shipar. Pareceres antigos permanecem em
`pipeline_artifacts` para auditoria; não serão deletados.

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
