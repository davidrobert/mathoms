/**
 * Desfecho terminal de um run, na forma que a UI consome (ADR-357 · A40.l21).
 *
 * Módulo puro: é aqui que a tabela de decisão da lane vira código, e é o único
 * lugar que os dois caminhos de notificação (WebSocket e polling) consultam —
 * `_mark_run_completed` do resume grava status sem publicar evento, então
 * existe terminal que só o polling enxerga.
 */
import type { PipelineEvent, PipelineRunStatus } from "./api";

export interface RunOutcome {
  /** Método de `toast` (sonner) que anuncia o desfecho. */
  toast: "success" | "warning" | "error" | "info";
  title: string;
  description?: string;
  durationMs: number;
  /** Run que produziu relatório leva o usuário ao entregável. */
  redirectToReports: boolean;
}

const OUTCOME_BY_STATUS: Partial<Record<PipelineRunStatus, RunOutcome>> = {
  completed: {
    toast: "success",
    title: "Relatório gerado com sucesso!",
    durationMs: 8000,
    redirectToReports: true,
  },
  partial_failure: {
    toast: "warning",
    title: "Relatório gerado com ressalva",
    // Genérica de propósito: 3 stages são degradáveis (ADR-357 §1) e o caminho
    // WS não tem `stage_logs` em mãos. Quem nomeia a lacuna é o banner.
    description: "Uma etapa final não foi concluída. O restante da análise está completo.",
    durationMs: 10000,
    redirectToReports: true,
  },
  failed: {
    toast: "error",
    title: "Não conseguimos concluir a análise.",
    description: "Verifique os detalhes da execução.",
    durationMs: 8000,
    redirectToReports: false,
  },
  cancelled: {
    toast: "info",
    title: "Processamento cancelado",
    durationMs: 4000,
    redirectToReports: false,
  },
};

/** Nomes de evento terminais — fallback quando o writer não manda `status`. */
const STATUS_BY_EVENT_NAME: Record<string, PipelineRunStatus> = {
  run_completed: "completed",
  run_failed: "failed",
  run_cancelled: "cancelled",
};

/** Terminal que entregou relatório — a pergunta "eu tenho relatório?". */
export function isDeliveredRun(status: string): boolean {
  return status === "completed" || status === "partial_failure";
}

export function terminalRunOutcome(status: string): RunOutcome | null {
  return OUTCOME_BY_STATUS[status as PipelineRunStatus] ?? null;
}

/**
 * Status do run a partir do evento terminal.
 *
 * `event.status` manda: ADR-357 §Consequências proíbe evento novo, e os dois
 * nomes admitidos (`run_completed`/`run_failed`) carregam o status real — o
 * leitor não depende de qual deles a A40.l18 escolher. O nome do evento é
 * fallback para writer que esqueça o parâmetro.
 */
export function runStatusFromEvent(event: PipelineEvent): PipelineRunStatus | null {
  // Discriminador é o NOME ser run-level, não a ausência de `stage`: um writer
  // que nomeie a etapa degradada no evento terminal continua sendo lido certo.
  // `status` é reusado por eventos de stage, que nunca casam este conjunto.
  if (!(event.event in STATUS_BY_EVENT_NAME)) return null;
  if (event.status && event.status in OUTCOME_BY_STATUS) {
    return event.status as PipelineRunStatus;
  }
  return STATUS_BY_EVENT_NAME[event.event];
}
