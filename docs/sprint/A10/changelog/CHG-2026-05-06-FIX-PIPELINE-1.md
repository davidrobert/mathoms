---
id: CHG-2026-05-06-FIX-PIPELINE-1
type: changelog-entry
date: "2026-05-06"
sprint: A10
adrs: ["[[ADR-080]]", "[[ADR-105]]", "[[ADR-157]]", "[[ADR-169]]"]
summary: |
  fix(pipeline): modo incremental respeitado por stages globais E1 (ADR-169 · 2026-05-06). - **fix(pipeline): modo incremental respeitado por stages globais E1 (ADR-169 · 2026-05-06):** Antes: clicar "Processar somente novos" reprocessava todas as dec
tags:
  - type/changelog-entry
  - sprint/a10
---


# fix(pipeline): modo incremental respeitado por stages globais E1 (ADR-169 · 2026-05-06)

- **fix(pipeline): modo incremental respeitado por stages globais E1 (ADR-169 · 2026-05-06):**
  Antes: clicar "Processar somente novos" reprocessava todas as declarações
  IRPF do workspace via LLM em `extract_irpf_full` (~7m + ~$0,70 cada — ADR-157),
  além de re-rodar `extract_members` e `extract_baseline` sobre todos os docs.
  Causa: ADR-080 limitou incremental a E0→E2; globals adicionados depois
  (ADR-105/127/157) ignoravam a flag.
  Fix: helper `pipeline/incremental.py` propaga `ctx.incremental_doc_paths`
  per-stage com semântica adaptada — `extract_irpf_full` filtra per-doc,
  `extract_baseline` filtra per-doc + agrega `E1.5a` do store
  (preservando paridade do consolidado), `extract_members` skipa quando
  zero overlap. Caso real do screenshot (5 IRPFs, 0 novos): de ~$3,50 +
  40min para `{"skipped": true}`. Cobertura de regressão em
  `tests/pipeline/test_incremental_globals.py` (20 testes).
