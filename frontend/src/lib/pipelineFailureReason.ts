import type { UserFacingError } from "./pipelineErrorMessages";

/**
 * Mensagem honesta para os 4 valores de `failure_reason` (A40.l27 · ADR-172/ADR-359).
 *
 * Por que precede `buildUserFacingError`: aquele deriva a mensagem do **texto de erro do
 * stage que falhou**, e nestes 4 casos não existe stage nenhum — o run morreu antes de
 * executar. Sem isto o usuário lê "o processamento travou no estágio inicial. Clique em
 * Reprocessar", que afirma duas coisas falsas: que houve estágio, e que travou.
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
};

/** `null` quando o motivo é ausente ou desconhecido — aí o caller mantém o texto do stage. */
export function messageForFailureReason(
  failureReason: string | null | undefined,
): UserFacingError | null {
  if (!failureReason) return null;
  return MENSAGENS[failureReason] ?? null;
}

/** Vocabulário coberto — espelha `ALL_REASONS` de `pipeline_failure_reasons.py`. */
export const FAILURE_REASONS_CONHECIDOS = Object.freeze(Object.keys(MENSAGENS));
