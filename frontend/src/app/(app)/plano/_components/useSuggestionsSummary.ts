"use client";

/**
 * ADR-161 (Onda 8 #5) — sumário de sugestões pendentes com severidade
 * dominante e contagem por categoria. Substitui `useSuggestionsCount`
 * em call-sites que precisam refletir severidade (banner em /plano).
 *
 * Falha silenciosa: erro de rede degrada para count=0 (banner some).
 */

import { useCallback, useEffect, useState } from "react";

import { getSuggestionsSummary, type SuggestionSeverity } from "@/lib/api";

export interface SuggestionsSummaryState {
  count: number;
  maxSeverity: SuggestionSeverity | null;
  byCategory: Record<string, number>;
  loading: boolean;
}

const EMPTY: SuggestionsSummaryState = {
  count: 0,
  maxSeverity: null,
  byCategory: {},
  loading: true,
};

export function useSuggestionsSummary(
  workspaceId: string | undefined,
): SuggestionsSummaryState {
  const [state, setState] = useState<SuggestionsSummaryState>(EMPTY);

  const reload = useCallback(async () => {
    if (!workspaceId) {
      setState({ ...EMPTY, loading: false });
      return;
    }
    setState((prev) => ({ ...prev, loading: true }));
    try {
      const resp = await getSuggestionsSummary(workspaceId);
      setState({
        count: resp.count,
        maxSeverity: resp.max_severity,
        byCategory: resp.by_category,
        loading: false,
      });
    } catch (err) {
      void err;
      setState({ ...EMPTY, loading: false });
    }
  }, [workspaceId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return state;
}
