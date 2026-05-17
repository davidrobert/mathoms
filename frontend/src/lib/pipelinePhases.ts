/**
 * Agrupamento narrativo das etapas do pipeline em 4 fases (ADR-068).
 *
 * O backend opera com 14+ etapas técnicas (E0-E7). A UI agrupa essas etapas
 * em 4 fases mentais que fazem sentido para o usuário final. Códigos
 * internos permanecem em logs/API/telemetria; o usuário vê fases.
 *
 * Regra de mapeamento:
 * - Toda etapa técnica pertence a exatamente uma fase.
 * - Etapas desconhecidas caem em "processing" (fallback defensivo).
 */

export type PhaseId = "preparing" | "reading" | "organizing" | "reporting";

export interface Phase {
  id: PhaseId;
  /** Número ordinal exibido no stepper (1-4). */
  order: number;
  /** Nome curto exibido no stepper. */
  title: string;
  /** Frase motivacional exibida quando esta fase está em execução. */
  activeMessage: string;
  /** Descrição educativa (tooltip / disclosure). */
  description: string;
  /** Etapas técnicas agrupadas sob esta fase. */
  stages: readonly string[];
}

export const PIPELINE_PHASES: readonly Phase[] = [
  {
    id: "preparing",
    order: 1,
    title: "Preparando seus documentos",
    activeMessage: "Verificando e organizando os arquivos enviados",
    description:
      "Conferimos se os arquivos estão íntegros, desbloqueamos PDFs com senha e organizamos cada documento pela sua categoria (extrato, fatura, IRPF, etc).",
    stages: [
      // Legacy keys (compat reverso F9.2 → F9.3).
      // E0-audit removido em ADR-213 (sunset stage audit_documents).
      "E0-route",
      "E0-unlock",
      // Descritivos canônicos (ADR-093).
      "route_documents",
      "unlock_documents",
    ],
  },
  {
    id: "reading",
    order: 2,
    title: "Lendo os dados",
    activeMessage: "Extraindo transações, saldos e posições dos seus documentos",
    description:
      "Lemos cada documento para identificar transações, saldos, investimentos e declarações — combinando parsers determinísticos e IA quando necessário.",
    stages: [
      // Legacy.
      "E1",
      "E1.5",
      "E1.5c",
      "E1.6",
      "E2-extratos",
      "E2-faturas",
      "E2-llm",
      "E2-informe-aluguel",
      // Descritivos.
      "extract_members",
      "extract_baseline",
      "consolidate_baseline",
      "extract_irpf_full",
      "extract_informe_aluguel",
      "extract_statements",
      "extract_invoices",
      "extract_with_llm",
    ],
  },
  {
    id: "organizing",
    order: 3,
    title: "Organizando suas finanças",
    activeMessage: "Reconciliando, categorizando e calculando seu patrimônio",
    description:
      "Removemos transações duplicadas, categorizamos receitas e despesas, e calculamos indicadores como patrimônio, fluxo de caixa e taxa de poupança.",
    stages: [
      // Legacy.
      "E3",
      "E4",
      "E5",
      "E5.N",
      // Descritivos.
      "reconcile_transactions",
      "categorize_transactions",
      "analyze_finances",
      "generate_narratives",
    ],
  },
  {
    id: "reporting",
    order: 4,
    title: "Montando seu relatório",
    activeMessage: "Gerando o relatório e revisando a consistência dos números",
    description:
      "Renderizamos o relatório, rodamos validações cruzadas para detectar inconsistências e geramos o parecer do planejador antes de entregar.",
    stages: [
      // Legacy.
      "E7-crossval",
      "E6-parecer",
      // Descritivos.
      "validate_cross",
      // ADR-199 — parecer planejador (review_finances_holistic) fecha o pipeline.
      "review_finances_holistic",
    ],
  },
] as const;

/** Índice reverso: código de etapa → id de fase (construído uma vez). */
const STAGE_TO_PHASE: Record<string, PhaseId> = (() => {
  const map: Record<string, PhaseId> = {};
  for (const phase of PIPELINE_PHASES) {
    for (const stage of phase.stages) {
      map[stage] = phase.id;
    }
  }
  return map;
})();

/** Retorna o id da fase à qual a etapa pertence. Fallback: "reading". */
export function phaseOfStage(stage: string | null | undefined): PhaseId {
  if (!stage) return "preparing";
  return STAGE_TO_PHASE[stage] ?? "reading";
}

/** Retorna o objeto Phase a partir do id ou da etapa. */
export function getPhase(idOrStage: PhaseId | string): Phase {
  const asPhase = PIPELINE_PHASES.find((p) => p.id === idOrStage);
  if (asPhase) return asPhase;
  const phaseId = phaseOfStage(idOrStage);
  return PIPELINE_PHASES.find((p) => p.id === phaseId) ?? PIPELINE_PHASES[0];
}

export type PhaseStatus =
  | "pending"
  | "active"
  | "completed"
  | "failed"
  | "needs_review";

export interface PhaseState {
  phase: Phase;
  status: PhaseStatus;
  /** Quantas etapas desta fase já terminaram (completed + skipped). */
  completedStages: number;
  /** Total de etapas DESTA EXECUÇÃO pertencentes a esta fase. */
  totalStages: number;
}

interface StageLike {
  stage: string;
  status: string;
}

interface PhaseContext {
  activePhaseId: string | null;
  failedPhaseId: string | null;
  isFailed: boolean;
  needsReview: boolean;
  runStatus: string;
}

function phaseStatusFor(
  phaseId: string,
  completedStages: number,
  totalStages: number,
  ctx: PhaseContext,
): PhaseStatus {
  if (ctx.failedPhaseId === phaseId) return "failed";
  if (ctx.needsReview && ctx.activePhaseId === phaseId) return "needs_review";
  if (ctx.activePhaseId === phaseId) return "active";
  if (totalStages > 0 && completedStages === totalStages && !ctx.isFailed) {
    return "completed";
  }
  // fase anterior à atual e sem logs ainda → considerar concluída se run completo
  if (ctx.runStatus === "completed" && totalStages === 0) return "completed";
  return "pending";
}

/**
 * Dado a lista de stage_logs de uma execução e a etapa corrente, retorna o
 * estado consolidado de cada uma das 4 fases. Usado pelo stepper.
 */
export function computePhaseStates(
  stageLogs: readonly StageLike[],
  currentStage: string | null | undefined,
  runStatus: string,
): PhaseState[] {
  const failedStage = stageLogs.find((s) => s.status === "failed");
  const ctx: PhaseContext = {
    activePhaseId: currentStage ? phaseOfStage(currentStage) : null,
    failedPhaseId: failedStage ? phaseOfStage(failedStage.stage) : null,
    isFailed: runStatus === "failed" || runStatus === "partial_failure",
    needsReview: runStatus === "needs_review",
    runStatus,
  };

  return PIPELINE_PHASES.map((phase) => {
    const logsForPhase = stageLogs.filter((s) => phase.stages.includes(s.stage));
    const completedStages = logsForPhase.filter((s) =>
      ["completed", "skipped", "skipped_free_tier"].includes(s.status),
    ).length;
    const totalStages = logsForPhase.length;
    const status = phaseStatusFor(phase.id, completedStages, totalStages, ctx);
    return { phase, status, completedStages, totalStages };
  });
}

/**
 * Progresso global derivado das 4 fases narrativas (não dos sub-stages
 * técnicos). Casa a leitura do stepper (`Fase 2 de 4`) com a barra de
 * progresso, evitando que stage_logs incompletos do backend produzam
 * 100% prematuramente.
 *
 * Contribuição por fase:
 *  - completed → 1.0
 *  - active|needs_review → 0.5 + 0.5 × (completedStages / totalStages)
 *    (mínimo 0.5 — fase ativa nunca conta como "vazia")
 *  - failed → completedStages / totalStages (mantém posição até onde foi)
 *  - pending → 0
 *
 * Retorna percentual inteiro ∈ [0..100].
 */
export function computePhaseProgress(states: readonly PhaseState[]): number {
  if (states.length === 0) return 0;
  let acc = 0;
  for (const s of states) {
    if (s.status === "completed") {
      acc += 1;
    } else if (s.status === "active" || s.status === "needs_review") {
      const ratio = s.totalStages > 0
        ? Math.min(1, s.completedStages / s.totalStages)
        : 0;
      acc += 0.5 + 0.5 * ratio;
    } else if (s.status === "failed") {
      acc += s.totalStages > 0
        ? Math.min(1, s.completedStages / s.totalStages)
        : 0;
    }
  }
  return Math.round((acc / states.length) * 100);
}
