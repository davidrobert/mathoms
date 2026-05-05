/**
 * Tradução de erros de `/auth/login` e `/auth/register` em mensagens
 * user-facing — headline curta + hint opcional. Espelha o padrão de
 * `pipelineErrorMessages.ts`.
 *
 * Motivação: antes, qualquer status ≠ 401/409 caía em `err.detail`, que
 * em muitos cenários (proxy retorna HTML, body vazio, FastAPI default)
 * vira "HTTP 500" — sem ação para o usuário e ruim p/ trust.
 */

import { ApiError, getErrorCode } from "./core";

export interface AuthErrorMessage {
  headline: string;
  hint: string | null;
}

const NETWORK_ERROR: AuthErrorMessage = {
  headline: "Erro de conexão com o servidor.",
  hint: "Verifique sua internet e tente novamente.",
};

const SERVER_ERROR: AuthErrorMessage = {
  headline: "Erro temporário no servidor.",
  hint: "Tente novamente em instantes — se persistir, recarregue a página.",
};

const RATE_LIMITED: AuthErrorMessage = {
  headline: "Muitas tentativas em pouco tempo.",
  hint: "Aguarde um instante antes de tentar de novo.",
};

/** `err.detail` que é apenas o placeholder genérico (`HTTP 500`,
 * `Internal Server Error`) — não é útil mostrar ao usuário. */
function isPlaceholderDetail(detail: string): boolean {
  return /^HTTP \d{3}$/i.test(detail) || /^internal server error$/i.test(detail);
}

export function loginErrorMessage(err: unknown): AuthErrorMessage {
  if (!(err instanceof ApiError)) return NETWORK_ERROR;

  if (err.status === 401) {
    return { headline: "Email ou senha incorretos.", hint: null };
  }
  if (err.status === 429) {
    if (getErrorCode(err) === "account_locked") {
      return {
        headline: "Conta temporariamente bloqueada.",
        hint: err.detail,
      };
    }
    return RATE_LIMITED;
  }
  if (err.status >= 500) return SERVER_ERROR;

  if (isPlaceholderDetail(err.detail)) return SERVER_ERROR;
  return { headline: err.detail, hint: null };
}

export function registerErrorMessage(err: unknown): AuthErrorMessage {
  if (!(err instanceof ApiError)) return NETWORK_ERROR;

  if (err.status === 409) {
    return {
      headline: "Este email já está cadastrado.",
      hint: "Use o link 'Entrar' abaixo.",
    };
  }
  if (err.status === 429) return RATE_LIMITED;
  if (err.status >= 500) return SERVER_ERROR;

  if (isPlaceholderDetail(err.detail)) return SERVER_ERROR;
  return { headline: err.detail, hint: null };
}
