---
id: CHG-2026-04-25-A10-A6G-2B-T3-PIPELINE-S
type: changelog-entry
date: "2026-04-25"
sprint: A10
commits: ["0a82790", "8d31d1c", "d6f511a", "fe20f3b", "ff0757c"]
summary: |
  A6g.2b T3 pipeline scripts decomp (goldens-safe). - **5 scripts com goldens** decompostos em orchestrators finos + helpers nomeados, paridade byte-a-byte preservada (1458 pipeline tests verdes em todos os commi
tags:
  - type/changelog-entry
  - sprint/a10
---


# A6g.2b T3 pipeline scripts decomp (goldens-safe)


- **5 scripts com goldens** decompostos em orchestrators finos +
  helpers nomeados, paridade byte-a-byte preservada (1458 pipeline
  tests verdes em todos os commits, incluindo
  `tests/test_e{3,4,5,5n}_golden_execution.py`):
  - `scripts/e7_review.py` — `run_cross_validation` 270 → 11 linhas
    + 14 helpers `_cv{1..14}_*` (cada um 7-25 linhas) + 2 tuplas de
    registro `_CV_OPTIONAL_CHECKS`/`_CV_ALWAYS_CHECKS`. Constante
    `_REQUIRED_CHARTS` extraída.
  - `scripts/e5n_narrativas.py` — `main_with_store` 76 → 32 linhas
    orquestrando 5 fases (`_e5n_print_header`, `_e5n_load_e5`,
    `_e5n_load_metrics`, `_e5n_build_and_validate`, `_e5n_persist`).
  - `scripts/e3_reconcile.py` — `main_with_store` 179 → 27 linhas
    orquestrando 7 fases (`_e3_build_adapter`, `_e3_run_reconciliation`,
    `_e3_validate_outputs`, `_e3_write_sidecar_logs`, `_e3_log_warnings`,
    `_e3_print_summary`, `_e3_build_result_dict`). Imports mortos
    (`generate_legacy_filename`, `ReconciliationService`) removidos.
  - `scripts/e4_categorize.py` — `main_with_store` 131 → 27 linhas
    orquestrando 5 fases (`_e4_build_adapter`, `_e4_persist_artifacts`,
    `_e4_write_qa_sidecar`, `_e4_print_summary`, `_e4_build_result_dict`).
    Import morto `all_filenames` removido.
  - `scripts/e5_analyze.py` — `main_with_store` 195 → 35 linhas
    orquestrando 10 fases (`_e5_init_workspace`, `_e5_load_md_inputs`,
    `_e5_check_e4_inputs`, `_e5_build_adapter`, `_e5_extract_legacy_dicts`,
    `_e5_resolve_periodo_dados`, `_e5_run_sanity_checks`,
    `_e5_compose_output`, `_e5_persist`, `_e5_print_summary`,
    `_e5_build_result_dict`). O anti-exemplo de 2998 linhas continua
    existindo (5 funções `analyze_*` legadas com >100 linhas), mas a
    entrada via Caminho B agora é orchestrator fino — restante depende
    de cleanup pós-F9.
- **Fora de escopo (preservado):** `main(root_dir)` legados não foram
  tocados — A6c.3 já os deletou (2026-04-24); reescritas adicionais em
  `analyze_*` ficam como work residual fora de A6g.
- **Commits:** `0a82790` (e7), `8d31d1c` (e5n), `d6f511a` (e3),
  `fe20f3b` (e4), `ff0757c` (e5).
