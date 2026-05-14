"use client";

// ADR-199 / ADR-208 — hook do aggregate PlannerReview.
//
// Single-fetch (não há list): carrega o parecer mais recente do report.
// 404 com code=not_generated_yet vira `state: 'not_generated'` para a UI
// renderizar placeholder educativo sem exibir erro técnico.

import { useCallback, useEffect, useState } from "react";

import {
  ApiError,
  getPlannerReview,
  type PlannerReviewResponse,
} from "@/lib/api";

export type PlannerReviewState =
  | { kind: "loading" }
  | { kind: "not_generated" }
  | { kind: "ready"; data: PlannerReviewResponse }
  | { kind: "error"; message: string };

export interface UsePlannerReviewResult {
  state: PlannerReviewState;
  reload: () => Promise<void>;
}

function describeError(err: unknown): string {
  if (err instanceof ApiError) {
    return err.detail;
  }
  return "Erro ao carregar parecer.";
}

async function _doFetch(
  workspaceId: string,
  reportId: string,
  setState: (s: PlannerReviewState) => void,
): Promise<void> {
  setState({ kind: "loading" });
  try {
    const data = await getPlannerReview(workspaceId, reportId);
    setState({ kind: "ready", data });
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      setState({ kind: "not_generated" });
      return;
    }
    setState({ kind: "error", message: describeError(err) });
  }
}

function _fetch_state(
  workspaceId: string | undefined,
  reportId: string | undefined,
  setState: (s: PlannerReviewState) => void,
): () => Promise<void> {
  return async () => {
    if (!workspaceId || !reportId) {
      setState({ kind: "not_generated" });
      return;
    }
    await _doFetch(workspaceId, reportId, setState);
  };
}

export function usePlannerReview(
  workspaceId: string | undefined,
  reportId: string | undefined,
): UsePlannerReviewResult {
  const [state, setState] = useState<PlannerReviewState>({ kind: "loading" });
  const reload = useCallback(_fetch_state(workspaceId, reportId, setState), [
    workspaceId,
    reportId,
  ]);
  useEffect(() => {
    void reload();
  }, [reload]);
  return { state, reload };
}
