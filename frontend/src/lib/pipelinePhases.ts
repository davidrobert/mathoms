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
    stages: ["E0-audit", "E0-route", "E0-unlock"],
  },
  {
    id: "reading",
    order: 2,
    title: "Lendo os dados",
    activeMessage: "Extraindo transações, saldos e posições dos seus documentos",
    description:
      "Lemos cada documento para identificar transações, saldos, investimentos e declarações — combinando parsers determinísticos e IA quando necessário.",
    stages: [
      "E1",
      "E1.5",
      "E1.5c",
      "E2-extratos",
      "E2-faturas",
      "E2-llm",
    ],
  },
  {
    id: "organizing",
    order: 3,
    title: "Organizando suas finanças",
    activeMessage: "Reconciliando, categorizando e calculando seu patrimônio",
    description:
      "Removemos transações duplicadas, categorizamos receitas e despesas, e calculamos indicadores como patrimônio, fluxo de caixa e taxa de poupança.",
    stages: ["E3", "E4", "E5", "E5.N"],
  },
  {
    id: "reporting",
    order: 4,
    title: "Montando seu relatório",
    activeMessage: "Gerando o relatório e revisando a consistência dos números",
    description:
      "Renderizamos o relatório HTML, rodamos validações cruzadas para detectar inconsistências e aplicamos a revisão final antes de entregar.",
    stages: ["E6", "E6-final", "E7-crossval", "E7-review", "E7-apply"],
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

/**
 * Dado a lista de stage_logs de uma execução e a etapa corrente, retorna o
 * estado consolidado de cada uma das 4 fases. Usado pelo stepper.
 */
export function computePhaseStates(
  stageLogs: readonly StageLike[],
  currentStage: string | null | undefined,
  runStatus: string,
): PhaseState[] {
  const activePhaseId = currentStage ? phaseOfStage(currentStage) : null;
  const isFailed = runStatus === "failed" || runStatus === "partial_failure";
  const needsReview = runStatus === "needs_review";

  // Qual fase alberga a etapa que falhou?
  const failedStage = stageLogs.find((s) => s.status === "failed");
  const failedPhaseId = failedStage ? phaseOfStage(failedStage.stage) : null;

  return PIPELINE_PHASES.map((phase) => {
    const logsForPhase = stageLogs.filter((s) => phase.stages.includes(s.stage));
    const completedStages = logsForPhase.filter((s) =>
      ["completed", "skipped", "skipped_free_tier"].includes(s.status),
    ).length;
    const totalStages = logsForPhase.length;

    let status: PhaseStatus = "pending";
    if (failedPhaseId === phase.id) {
      status = "failed";
    } else if (needsReview && activePhaseId === phase.id) {
      status = "needs_review";
    } else if (activePhaseId === phase.id) {
      status = "active";
    } else if (
      totalStages > 0 &&
      completedStages === totalStages &&
      !isFailed
    ) {
      status = "completed";
    } else if (
      // fase anterior à atual e sem logs ainda → considerar concluída se run completo
      runStatus === "completed" &&
      totalStages === 0
    ) {
      status = "completed";
    }

    return { phase, status, completedStages, totalStages };
  });
}
