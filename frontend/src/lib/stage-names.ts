/**
 * Nomes user-facing das etapas do pipeline (ADR-068).
 *
 * Regra: UI, toasts, e-mails e notificações NUNCA mostram códigos `E*`.
 * Códigos continuam preservados em logs, API, WebSocket e telemetria
 * para observabilidade e suporte.
 *
 * Ver também: `PIPELINE_PHASES` em `./pipelinePhases.ts` — agrupamento
 * de 4 fases narrativas para o stepper de alto nível.
 */
export const STAGE_DISPLAY_NAMES: Record<string, string> = {
  // F9.2+ descriptive keys (canônicas — ADR-093). Legacy keys abaixo
  // permanecem enquanto rows DB ainda gravam no formato antigo (até F9.3).
  "audit_documents": "Verificação dos arquivos",
  "unlock_documents": "Desbloqueio de PDFs com senha",
  "route_documents": "Identificação do tipo de cada documento",
  "extract_members": "Leitura dos dados da família",
  "extract_baseline": "Leitura da declaração de Imposto de Renda",
  "extract_irpf_full": "Leitura completa da declaração de Imposto de Renda",
  "consolidate_baseline": "Cálculo do patrimônio inicial",
  "extract_invoices": "Leitura das faturas de cartão",
  "extract_statements": "Leitura dos extratos bancários",
  "extract_with_llm": "Leitura dos extratos de investimentos",
  "reconcile_transactions": "Remoção de transações duplicadas",
  "categorize_transactions": "Categorização de receitas e despesas",
  "analyze_finances": "Cálculo de indicadores financeiros",
  "generate_narratives": "Geração de análises e comentários",
  "validate_cross": "Conferência da consistência dos números",
  "review_finances": "Revisão final do relatório",
  "apply_review": "Aplicação dos ajustes da revisão",
  "review_finances_holistic": "Parecer do planejador financeiro",
  // Legacy (compat reverso F9.2 → F9.3)
  "E0-audit": "Verificação dos arquivos",
  "E0-route": "Identificação do tipo de cada documento",
  "E0-unlock": "Desbloqueio de PDFs com senha",
  "E1": "Leitura dos dados da família",
  "E1.5": "Leitura da declaração de Imposto de Renda",
  "E1.5c": "Cálculo do patrimônio inicial",
  "E1.6": "Leitura completa da declaração de Imposto de Renda",
  "E2": "Leitura de transações",
  "E2-llm": "Leitura dos extratos de investimentos",
  "E2-extratos": "Leitura dos extratos bancários",
  "E2-faturas": "Leitura das faturas de cartão",
  "E3": "Remoção de transações duplicadas",
  "E4": "Categorização de receitas e despesas",
  "E5": "Cálculo de indicadores financeiros",
  "E5.N": "Geração de análises e comentários",
  "E7-crossval": "Conferência da consistência dos números",
  "E7-review": "Revisão final do relatório",
  "E7-apply": "Aplicação dos ajustes da revisão",
  "E6-parecer": "Parecer do planejador financeiro",
};

/**
 * Traduz código interno de etapa (ex: "E3") para nome user-facing.
 * Fallback: retorna o código original quando não mapeado (não deve acontecer).
 */
export function stageName(stage: string): string {
  return STAGE_DISPLAY_NAMES[stage] ?? stage;
}
