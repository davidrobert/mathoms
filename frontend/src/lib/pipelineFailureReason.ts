import type { UserFacingError } from "./pipelineErrorMessages";

/**
 * Mensagem honesta para os valores de `failure_reason` (A40.l27 · ADR-172/ADR-359/ADR-446).
 *
 * Por que precede `buildUserFacingError`: aquele deriva a mensagem do **texto de erro do
 * stage que falhou**, e aqui a causa é do run, não do stage: ou não há texto de stage, ou
 * ele só registra o corte (`time_limit_exceeded`). Sem isto o usuário lê "o processamento
 * travou no estágio inicial. Clique em Reprocessar", que afirma duas coisas falsas: que
 * houve estágio, e que travou.
 */
const MENSAGENS: Record<string, UserFacingError> = {
  dispatch_failed: {
    headline: "Não foi possível iniciar o processamento",
    hint: "O serviço de processamento recusou a solicitação. Tente novamente em alguns instantes — nada foi processado.",
  },
  dispatch_unconfirmed: {
    headline: "O processamento não foi iniciado",
    hint: "A solicitação foi registrada mas nenhum processador a assumiu. Nada foi processado; pode disparar de novo.",
  },
  run_setup_failed: {
    headline: "Falha ao preparar o processamento",
    hint: "A preparação dos seus dados falhou antes de começar. Se repetir, acione o suporte.",
  },
  heartbeat_timeout: {
    headline: "O processamento parou de responder",
    hint: "A execução foi interrompida sem concluir. Reprocessar retoma do ponto seguro.",
  },
  time_limit_exceeded: {
    headline: "O processamento atingiu o tempo limite",
    hint: "As etapas concluídas foram salvas. Reprocessar retoma da etapa em que parou; se repetir, acione o suporte.",
  },
};

/**
 * Motivos cujo hint manda retomar: neles "Reprocessar a partir de" é a ação primária.
 * "Tentar novamente" refaz o run inteiro, inclusive o trabalho que já gastou o tempo
 * limite, e paga a IA de novo (ADR-446).
 */
const RETOMADA_PRIMEIRO = new Set(["heartbeat_timeout", "time_limit_exceeded"]);

export function prefersResumeFromStage(failureReason: string | null | undefined): boolean {
  return !!failureReason && RETOMADA_PRIMEIRO.has(failureReason);
}

/** `null` quando o motivo é ausente ou desconhecido — aí o caller mantém o texto do stage. */
export function messageForFailureReason(
  failureReason: string | null | undefined,
): UserFacingError | null {
  if (!failureReason) return null;
  return MENSAGENS[failureReason] ?? null;
}

/** Vocabulário coberto — espelha `ALL_REASONS` de `pipeline_failure_reasons.py`. */
export const FAILURE_REASONS_CONHECIDOS = Object.freeze(Object.keys(MENSAGENS));
