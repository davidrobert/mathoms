/**
 * Espelha `STAGE_RENAME_MAP` em `pipeline/stage_spec.py` (ADR-093 / F9.2).
 *
 * Pós-rename F9.2, `current_stage`, `stage_logs[].stage` e a maior parte
 * dos eventos WS chegam em formato descritivo. Mas emissores de
 * `stage_activity` em `pipeline/stages/*.py` e `scripts/e2_extract.py`
 * ainda passam keys legadas (ex.: `"E2-extratos"`). Use
 * `resolveStageName()` em qualquer boundary que receba `stage` do WS para
 * normalizar.
 */
const LEGACY_TO_DESCRIPTIVE: Record<string, string> = {
  "E0-audit": "audit_documents",
  "E0-unlock": "unlock_documents",
  "E0-route": "route_documents",
  "E1": "extract_members",
  "E1.5": "extract_baseline",
  "E1.5c": "consolidate_baseline",
  "E2-faturas": "extract_invoices",
  "E2-extratos": "extract_statements",
  "E2-llm": "extract_with_llm",
  "E3": "reconcile_transactions",
  "E4": "categorize_transactions",
  "E5": "analyze_finances",
  "E5.N": "generate_narratives",
  "E7-crossval": "validate_cross",
  "E7-review": "review_finances",
  "E7-apply": "apply_review",
  "E5-revised": "analyze_finances_revised",
};

export function resolveStageName(stage: string): string {
  return LEGACY_TO_DESCRIPTIVE[stage] ?? stage;
}
