import { resolveStageName } from "./pipelineStageNames";

/**
 * Etapas que usam LLM no orchestrador. Manter alinhado a
 * `LLM_STAGES` em `pipeline/orchestrator.py`. Aceita legacy ou
 * descritivo via `resolveStageName` (F9.2).
 */
const PIPELINE_LLM_STAGES = new Set([
  "extract_members",
  "extract_baseline",
  "extract_with_llm",
  "review_finances",
]);

export function isPipelineLlmStage(stage: string): boolean {
  return PIPELINE_LLM_STAGES.has(resolveStageName(stage));
}
