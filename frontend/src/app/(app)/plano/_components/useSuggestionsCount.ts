"use client";

/**
 * Direção E · Onda 5 · ADR-153 — contagem de sugestões pendentes do
 * último relatório (impl real). Substitui o stub Onda 4.
 *
 * Mesma assinatura do stub para que `SuggestionsBanner` em `/plano` e
 * `ActionStatusBar` em `/acao` continuem funcionando sem mudança no
 * call-site.
 */

import { useCallback, useEffect, useState } from "react";

import { countSuggestions } from "@/lib/api";

export interface SuggestionsCountState {
  count: number;
  loading: boolean;
}

export function useSuggestionsCount(
  workspaceId: string | undefined,
): SuggestionsCountState {
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    if (!workspaceId) {
      setCount(0);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const resp = await countSuggestions(workspaceId, "Pendente");
      setCount(resp.count);
    } catch (err) {
      // Falha silenciosa no banner — UI degrada para count=0 (banner some).
      // Banner de sugestões é cosmético; toast aqui geraria ruído visual.
      void err;
      setCount(0);
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { count, loading };
}
