import type { PipelineEvent, PipelineStageActivity } from "./api";

/**
 * Espelha `STAGE_RENAME_MAP` em `pipeline/stage_spec.py` (ADR-093 / F9.2).
 *
 * Pós-rename F9.2, `current_stage`, `stage_logs[].stage` e a maior parte
 * dos eventos WS chegam em formato descritivo. Mas emissores de
 * `stage_activity` em `pipeline/stages/*.py` e `scripts/extract_bank_documents.py`
 * ainda passam keys legadas (ex.: `"E2-extratos"`). Use
 * `resolveStageName()` em qualquer boundary que receba `stage` do WS para
 * normalizar.
 */
const LEGACY_TO_DESCRIPTIVE: Record<string, string> = {
  "E0-unlock": "unlock_documents",
  "E0-route": "route_documents",
  "E1": "extract_members",
  "E1.5": "extract_baseline",
  "E1.5c": "consolidate_baseline",
  "E1.6": "extract_irpf_full",
  "E2-faturas": "extract_invoices",
  "E2-extratos": "extract_statements",
  "E2-llm": "extract_with_llm",
  "E2-informe-aluguel": "extract_informe_aluguel",
  "E2-informe-anual": "extract_informes_anuais",
  "E2-comprovante-bem": "extract_comprovantes_bens",
  "E3": "reconcile_transactions",
  "E4": "categorize_transactions",
  "E5": "analyze_finances",
  "E5.N": "generate_narratives",
  "E7-crossval": "validate_cross",
  "E6-parecer": "review_finances_holistic",
};

export function resolveStageName(stage: string): string {
  return LEGACY_TO_DESCRIPTIVE[stage] ?? stage;
}

const VALID_PHASES = [
  "preparing",
  "awaiting_llm",
  "validating",
  "persisting",
  "finalizing",
] as const;

/**
 * Converte um evento WS `stage_activity` em `PipelineStageActivity`,
 * normalizando o `stage` para o nome descritivo (ADR-093). Retorna
 * `null` se o evento não tem `stage` ou não é um `stage_activity`.
 *
 * Função pura — extraída do handler em `app/(app)/pipeline/page.tsx`
 * para ser testada sem render. Garante a invariante: o `stage` que
 * sai daqui sempre é o descritivo, alinhado com `stage_logs[].stage`.
 */
export function parseStageActivityEvent(
  event: PipelineEvent,
): PipelineStageActivity | null {
  if (event.event !== "stage_activity" || !event.stage) return null;
  const d = event.detail ?? {};
  const phase = typeof d.phase === "string" ? d.phase : undefined;
  return {
    stage: resolveStageName(event.stage),
    file: typeof d.file === "string" ? d.file : undefined,
    message: typeof d.message === "string" ? d.message : undefined,
    currentItem:
      typeof d.current_item === "string" ? d.current_item : undefined,
    itemsDone: typeof d.items_done === "number" ? d.items_done : undefined,
    itemsTotal:
      typeof d.items_total === "number" ? d.items_total : undefined,
    phase:
      phase && (VALID_PHASES as readonly string[]).includes(phase)
        ? (phase as (typeof VALID_PHASES)[number])
        : undefined,
    estimatedDurationMs:
      typeof d.estimated_duration_ms === "number"
        ? d.estimated_duration_ms
        : undefined,
  };
}
