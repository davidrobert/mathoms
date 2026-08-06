import type { PipelineRunResponse } from "@/lib/api";

/**
 * ADR-357 §3: run degradado **não** popula `failed_at_stage` — a etapa que não
 * entregou sai de `stage_logs`. Irmão de `deriveFailedStage`, que continua
 * cego a `degraded` de propósito.
 */
export function deriveDegradedStage(
  run: Pick<PipelineRunResponse, "stage_logs">,
): string | null {
  return run.stage_logs.find((s) => s.status === "degraded")?.stage ?? null;
}

// Uma frase por membro degradável (ADR-357 §1). Template genérico sobre
// `stageName()` erraria concordância de gênero e vazaria nome de etapa técnica.
const CAVEAT_BY_STAGE: Record<string, string> = {
  review_finances_holistic: "Relatório gerado, sem o parecer do planejador.",
  "E6-parecer": "Relatório gerado, sem o parecer do planejador.",
  generate_narratives: "Relatório gerado, sem as análises e comentários.",
  "E5.N": "Relatório gerado, sem as análises e comentários.",
  validate_cross: "Relatório gerado, sem a conferência de consistência dos números.",
  "E7-crossval": "Relatório gerado, sem a conferência de consistência dos números.",
};

const CAVEAT_FALLBACK = "Relatório gerado, com uma etapa final incompleta.";

export function degradedRunCaveat(
  run: Pick<PipelineRunResponse, "stage_logs">,
): string {
  const stage = deriveDegradedStage(run);
  return (stage && CAVEAT_BY_STAGE[stage]) || CAVEAT_FALLBACK;
}
