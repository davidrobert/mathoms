/**
 * Etapas que usam LLM no orchestrador. Manter alinhado a
 * `LLM_STAGES` em `pipeline/orchestrator.py`.
 */
const PIPELINE_LLM_STAGES = new Set(["E1", "E1.5", "E2-llm", "E7-review"]);

export function isPipelineLlmStage(stage: string): boolean {
  return PIPELINE_LLM_STAGES.has(stage);
}
