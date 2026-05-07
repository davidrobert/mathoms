---
id: A6a
type: lane
title: "LLM stages escrevendo via `ArtifactStore`"
sprint: A6
status: shipped
priority: P0
ship_date: "2026-04-19"
adrs: ["[[ADR-105]]", "[[ADR-127]]", "[[ADR-128]]"]
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a6
  - status/shipped
  - priority/p0
---


# A6a — LLM stages escrevendo via `ArtifactStore`


| # | Entrega | Prio | Esforço | Status |
| --- | --- | --- | --- | --- |
| A6a.1 | `pipeline/stages/e15.py` troca `out_path.write_text` por `store.write("E1.5", "baseline_patrimonial", ...)` → produz `-1.5_baseline.json` | P0 | 1h | ✅ |
| A6a.2 | `pipeline/stages/e2_llm.py` troca `out_path.write_text` por `store.write("E2-llm", stem, e2_json)`; `_find_unprocessed_docs` via `store.list_keys` | P0 | 1h | ✅ |
| A6a.3 | Critérios estruturais + integration tests com DiskArtifactStore em `tests/test_llm_stages.py` (4 testes novos) | P0 | 1h | ✅ |
| A6a.4 | ADR-105: E1 (config, não artefato) e E7-review LLM (ad-hoc) **não migram** — decisão documentada | P2 | 15min | ✅ |
| A6a.5 | **Revisada 2026-04-24 (ADR-127):** E1 migrada para `store.write("E1", "members", ...)`; mapping registrado; ADR-105 reinterpretada (E1 é artefato de domínio, não só config) | P1 | 1h | ✅ |
| A6a.6 | **Revisada 2026-04-24 (ADR-128):** E7-review-llm migrada para `ArtifactStore` — `store.read("E5", ...)` + `list_keys("E7-crossval")` + `store.write("E7-review", "review_llm", ...)`; teste em `InMemoryArtifactStore`. ADR-105 reinterpretada (E7-review é stage determinístico em cima de input LLM — deve ser stateless) | P1 | 1h | ✅ |

**Checkpoint A6a:** ✅ `MATHOMS_USE_DB_ARTIFACTS=true` pode ser ativado sem quebrar E3→E7.
