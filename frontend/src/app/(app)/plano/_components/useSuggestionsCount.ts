"use client";

/**
 * Direção E · Onda 4 — placeholder hook para contagem de sugestões pendentes.
 *
 * Aggregate `Suggestion` ainda não existe no backend (Onda 5 entregará
 * tabela + endpoints + pipeline E5 que gera sugestões). Por enquanto
 * retorna sempre 0 — banner em `/plano` fica oculto. Quando Onda 5
 * ligar o endpoint, basta trocar o stub pela chamada real (mesma
 * assinatura do hook permanece).
 */

export interface SuggestionsCountState {
  count: number;
  loading: boolean;
}

export function useSuggestionsCount(
  workspaceId: string | undefined,
): SuggestionsCountState {
  // Stub determinístico até Onda 5 (Suggestion full-stack).
  // Mantém referência a workspaceId para o linter aceitar e para
  // sinalizar que o hook é workspace-scoped quando real.
  void workspaceId;
  return { count: 0, loading: false };
}
