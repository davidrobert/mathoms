---
id: CHG-2026-05-14-REFACTOR-REMOVE-REVIEW-FINANCES
type: changelog-entry
date: "2026-05-14"
sprint: A12
lane: "[[A12.planner-review-cleanup]]"
prs: []
commits: []
summary: |
  refactor(pipeline): remove stage `review_finances` (E7-review) + dependente
  `apply_review` (E7-apply) e respectivo dead code. Superseded por ADR-199.
breaking: true
tags:
  - type/changelog-entry
  - sprint/a12
  - area/llm
  - area/pipeline
  - area/report
adrs:
  - "[[ADR-128]]"
  - "[[ADR-199]]"
---

# refactor(pipeline): remove review_finances + apply_review (ADR-199)

Stage `review_finances` (E7-review) e seu dependente direto `apply_review`
(E7-apply) foram supersedidos por `review_finances_holistic` (parecer
planejador) nos Atos 1-6 do plano
[`PLANNER_REVIEW`](../../../archive/PLANNER_REVIEW-2026-07-09.md) (PRs #242-#250).

Output legacy era órfão — nenhum endpoint, componente React ou aggregate
consumia `("E7-review", "review_llm")` nem `("E7-apply", "analyze_finances_revised")`.
Confirmado via varredura exaustiva pré-cutover.

**Escopo de remoção:**

- **Runtime pipeline:**
  - Deletados: `pipeline/stages/review_finances.py`, `pipeline/stages/e7.py`,
    `pipeline/llm/prompts/e7_review.py`, `pipeline/llm/schemas/e7_review.py`
  - Substituído `pipeline/stages/e7.py::run_crossval` pelo módulo descritivo
    padrão `pipeline/stages/validate_cross.py::run`
  - `STAGE_REGISTRY` / `FULL_ORDER` / `STAGE_RENAME_MAP` / `_STAGE_RUNNERS`:
    entries `review_finances`, `apply_review`, `E7-review`, `E7-apply`,
    `E5-revised` removidas
  - `_STAGE_TO_DIR` / `_STAGE_TO_SUFFIX`: entries `E7-review`, `E7-apply`
    removidas; `validate_cross` ganha entry
  - `VIRTUAL_ARTIFACT_STAGES`: `analyze_finances_revised` removido
    (frozenset vazio agora)
  - `StageSpec.is_deprecated` flag removida (YAGNI — único caller foi removido)
  - `ctx.e7_dir` removido (refencias cosméticas sem caller real)
- **CLI dev:** `scripts/e_reset.py` refatorado — drops LLM_STAGES,
  DETERMINISTIC_SCRIPTS, EXECUTION_ORDER_*, RESET_WALLS, LLM_DESCRIPTIONS,
  STAGE_EXTRA_ARGS entries; remove `strip_review_from_e5_files`,
  `REVIEW_TEMPLATE_PATH`
- **scripts/e7_review.py:** refactor cirúrgico — mantém os 14 checks
  CV1-CV14 usados por `validate_cross`; remove `build_review_template`,
  `validate_review`, `apply_review`, `strip_review_from_e5`,
  `extract_persona_from_methodology`, `load_methodology`, `load_e5_json`
  (todos dead code após cutover)
- **Backend:** `retry_config.py` entry "E7-review" repurposed para
  `review_finances_holistic`; `backfill_artifacts_from_disk.py` drop;
  docstrings em `pipeline_service.py` / `config_blob/response.py` atualizadas
- **Frontend:** `stage-names.ts`, `pipelineStageNames.ts`,
  `pipelineLlmStages.ts`, `pipelinePhases.ts`: labels/mappings atualizados;
  novo label "Parecer do planejador" para `E6-parecer` / `review_finances_holistic`
- **Testes:** 3 arquivos deletados (`test_llm_stages_e7.py`,
  `test_review_finances_deprecation.py`, golden JSON);
  10+ arquivos editados para remover imports/asserts órfãos

**Preserved como histórico:**

- [[ADR-128]] (Decision record) — frontmatter `phase` atualizado para
  "Removed em A12.X"
- Migration Alembic `q5r6s7t8u9v0_rename_stage_identifiers` — imutável
  por design
- Artifacts `("E7-review", "review_llm")` / `("E7-apply", ...)` antigos
  em `pipeline_artifacts` — política de retenção opção A (não purgar;
  histórico auditável)

**Total:** ~42 arquivos tocados; 6 deletados; -1100 linhas líquidas.
