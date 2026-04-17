import { isPipelineLlmStage } from "./pipelineLlmStages";

/**
 * Explica o impacto da revisão pausada (F11.5c) — sem códigos E* na UI (ADR-068).
 */
export function reviewPauseImpactHint(
  pausedAtStage: string | null | undefined,
): string {
  if (!pausedAtStage) {
    return "Revise os resultados antes de aprovar. Eles alimentam categorias, saldos e textos do relatório.";
  }
  if (pausedAtStage === "E4" || pausedAtStage.startsWith("E7")) {
    return "O que você aprovar aqui pode alterar categorias, textos e recomendações no relatório final.";
  }
  if (
    pausedAtStage === "E3" ||
    pausedAtStage.startsWith("E2") ||
    pausedAtStage === "E5" ||
    pausedAtStage === "E5.N"
  ) {
    return "O que você aprovar aqui pode alterar transações, saldos consolidados e números exibidos no relatório.";
  }
  return "Revise os resultados antes de aprovar; eles alimentam o relatório.";
}

/** Texto curto para etapas com LLM (F11.5a) — opcionalmente exibido ao lado do nome da etapa. */
export function stageLlmFootnote(stage: string): string | null {
  if (!isPipelineLlmStage(stage)) return null;
  return "Leitura assistida por IA — confira valores antes de aprovar.";
}
