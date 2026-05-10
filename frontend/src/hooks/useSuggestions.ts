"use client";

// Direção E · Onda 5 · ADR-153 — hook do aggregate Suggestion.
// Carrega lista do workspace (filtra opcionalmente por status), expõe
// mutações que invalidam (refetch). Padrão minimal — alinhado ao
// `useDecisions` (sem cache global; cada consumer chama reload).

import { useCallback, useEffect, useState } from "react";

import {
  ApiError,
  acceptSuggestion as apiAccept,
  dismissSuggestion as apiDismiss,
  listSuggestions as apiList,
  modifySuggestion as apiModify,
  regenerateSuggestionsForReport as apiRegenerate,
  type AcceptSuggestionPayload,
  type DismissSuggestionPayload,
  type ModifySuggestionPayload,
  type Suggestion,
  type SuggestionRegenerateResponse,
  type SuggestionAggregateStatus,
} from "@/lib/api";

export interface UseSuggestionsState {
  suggestions: Suggestion[];
  loading: boolean;
  error: string;
  reload: () => Promise<void>;
  accept: (
    suggestionId: string,
    payload: AcceptSuggestionPayload,
  ) => Promise<Suggestion>;
  modify: (
    suggestionId: string,
    payload: ModifySuggestionPayload,
  ) => Promise<Suggestion>;
  dismiss: (
    suggestionId: string,
    payload: DismissSuggestionPayload,
  ) => Promise<Suggestion>;
  regenerate: (reportId: string) => Promise<SuggestionRegenerateResponse>;
}

type Reload = () => Promise<void>;

function describeError(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.detail : fallback;
}

export function useSuggestions(
  workspaceId: string | undefined,
  status?: SuggestionAggregateStatus,
): UseSuggestionsState {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const reload = useReload({
    workspaceId,
    status,
    setSuggestions,
    setLoading,
    setError,
  });

  const mutators = useMutators(workspaceId, reload);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { suggestions, loading, error, reload, ...mutators };
}

interface ReloadDeps {
  workspaceId: string | undefined;
  status: SuggestionAggregateStatus | undefined;
  setSuggestions: (s: Suggestion[]) => void;
  setLoading: (b: boolean) => void;
  setError: (s: string) => void;
}

function useReload({
  workspaceId,
  status,
  setSuggestions,
  setLoading,
  setError,
}: ReloadDeps): Reload {
  return useCallback(async () => {
    if (!workspaceId) {
      setSuggestions([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const resp = await apiList(workspaceId, status);
      setSuggestions(Array.isArray(resp?.suggestions) ? resp.suggestions : []);
    } catch (err) {
      setError(describeError(err, "Erro ao carregar sugestões"));
    } finally {
      setLoading(false);
    }
  }, [workspaceId, status, setSuggestions, setLoading, setError]);
}

interface Mutators {
  accept: UseSuggestionsState["accept"];
  modify: UseSuggestionsState["modify"];
  dismiss: UseSuggestionsState["dismiss"];
  regenerate: UseSuggestionsState["regenerate"];
}

function useMutators(
  workspaceId: string | undefined,
  reload: Reload,
): Mutators {
  return {
    accept: useAccept(workspaceId, reload),
    modify: useModify(workspaceId, reload),
    dismiss: useDismiss(workspaceId, reload),
    regenerate: useRegenerate(workspaceId, reload),
  };
}

function useAccept(workspaceId: string | undefined, reload: Reload) {
  return useCallback(
    async (suggestionId: string, payload: AcceptSuggestionPayload) => {
      if (!workspaceId) throw new Error("Workspace não selecionado");
      const out = await apiAccept(workspaceId, suggestionId, payload);
      await reload();
      return out;
    },
    [workspaceId, reload],
  );
}

function useModify(workspaceId: string | undefined, reload: Reload) {
  return useCallback(
    async (suggestionId: string, payload: ModifySuggestionPayload) => {
      if (!workspaceId) throw new Error("Workspace não selecionado");
      const out = await apiModify(workspaceId, suggestionId, payload);
      await reload();
      return out;
    },
    [workspaceId, reload],
  );
}

function useDismiss(workspaceId: string | undefined, reload: Reload) {
  return useCallback(
    async (suggestionId: string, payload: DismissSuggestionPayload) => {
      if (!workspaceId) throw new Error("Workspace não selecionado");
      const out = await apiDismiss(workspaceId, suggestionId, payload);
      await reload();
      return out;
    },
    [workspaceId, reload],
  );
}

function useRegenerate(workspaceId: string | undefined, reload: Reload) {
  return useCallback(
    async (reportId: string) => {
      if (!workspaceId) throw new Error("Workspace não selecionado");
      const out = await apiRegenerate(workspaceId, reportId);
      await reload();
      return out;
    },
    [workspaceId, reload],
  );
}
