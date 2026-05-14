"use client";

// ADR-153 / ADR-199 Ato 5 — wrapper de ações sobre Suggestion(origin='llm').
//
// Frontend resolve `dedup_key` da sugestão LLM → busca Suggestion no
// workspace → chama endpoints existentes (accept/dismiss). Não há
// endpoint novo; o aggregate Suggestion foi materializado pelo
// `_record_stage_result` (PlannerReviewPersistence) com `dedup_key`
// estável.

import { useCallback } from "react";

import {
  acceptSuggestion,
  dismissSuggestion,
  listSuggestions,
  type Suggestion,
} from "@/lib/api";

export interface SuggestionAcceptArgs {
  /** ID interno (UUID) ou dedup_key (sha256 64-hex) — hook resolve internamente. */
  suggestionRef: string;
  decisionCode: string;
  note?: string;
}

export interface SuggestionDismissArgs {
  suggestionRef: string;
  reason: "nao_se_aplica" | "discordo_diagnostico" | "outro" | "ja_considerei";
  note?: string;
}

export interface UseSuggestionActionsResult {
  accept: (args: SuggestionAcceptArgs) => Promise<Suggestion>;
  dismiss: (args: SuggestionDismissArgs) => Promise<Suggestion>;
  /** Resolve dedup_key (64-hex) → Suggestion no workspace. */
  resolveByDedupKey: (dedupKey: string) => Promise<Suggestion | null>;
}

const _SHA256_RE = /^[a-f0-9]{64}$/;

function useResolveByDedupKey(
  workspaceId: string | undefined,
): (dedupKey: string) => Promise<Suggestion | null> {
  return useCallback(
    async (dedupKey: string) => {
      if (!workspaceId) return null;
      const resp = await listSuggestions(workspaceId, "Pendente");
      return resp.suggestions.find((s) => s.dedup_key === dedupKey) ?? null;
    },
    [workspaceId],
  );
}

function useResolveId(
  resolveByDedupKey: (k: string) => Promise<Suggestion | null>,
): (ref: string) => Promise<string> {
  return useCallback(
    async (ref: string) => {
      if (!_SHA256_RE.test(ref)) return ref; // já é UUID
      const sugg = await resolveByDedupKey(ref);
      if (!sugg) throw new Error("Sugestão não encontrada no workspace.");
      return sugg.id;
    },
    [resolveByDedupKey],
  );
}

function useAcceptAction(
  workspaceId: string | undefined,
  resolveId: (ref: string) => Promise<string>,
) {
  return useCallback(
    async (args: SuggestionAcceptArgs): Promise<Suggestion> => {
      if (!workspaceId) throw new Error("Workspace não selecionado");
      const id = await resolveId(args.suggestionRef);
      return acceptSuggestion(workspaceId, id, {
        decision_code: args.decisionCode,
        note: args.note,
      });
    },
    [workspaceId, resolveId],
  );
}

function useDismissAction(
  workspaceId: string | undefined,
  resolveId: (ref: string) => Promise<string>,
) {
  return useCallback(
    async (args: SuggestionDismissArgs): Promise<Suggestion> => {
      if (!workspaceId) throw new Error("Workspace não selecionado");
      const id = await resolveId(args.suggestionRef);
      return dismissSuggestion(workspaceId, id, {
        reason: args.reason,
        note: args.note,
      });
    },
    [workspaceId, resolveId],
  );
}

export function useSuggestionActions(
  workspaceId: string | undefined,
): UseSuggestionActionsResult {
  const resolveByDedupKey = useResolveByDedupKey(workspaceId);
  const resolveId = useResolveId(resolveByDedupKey);
  const accept = useAcceptAction(workspaceId, resolveId);
  const dismiss = useDismissAction(workspaceId, resolveId);
  return { accept, dismiss, resolveByDedupKey };
}
