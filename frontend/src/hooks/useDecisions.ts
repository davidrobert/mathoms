"use client";

// A7.2a · ADR-136 — hook do aggregate Decision.
// Carrega a lista do workspace, expõe ações de mutação que invalidam
// (refetch) ao concluir. Padrão minimal — sem cache global; cada consumer
// pode adotar SWR/React Query depois se houver demanda.

import { useCallback, useEffect, useState } from "react";

import {
  ApiError,
  type Decision,
  type DecisionExecutePayload,
  type DecisionSupersedePayload,
  type DecisionUpdatePayload,
  executeDecision,
  listDecisions,
  supersedeDecision,
  updateDecision,
} from "@/lib/api";

export interface UseDecisionsState {
  decisions: Decision[];
  loading: boolean;
  error: string;
  reload: () => Promise<void>;
  execute: (decisionId: string, payload?: DecisionExecutePayload) => Promise<void>;
  update: (decisionId: string, payload: DecisionUpdatePayload) => Promise<void>;
  supersede: (oldId: string, payload: DecisionSupersedePayload) => Promise<void>;
}

function describeError(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.detail : fallback;
}

export function useDecisions(workspaceId: string | undefined): UseDecisionsState {
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    if (!workspaceId) {
      setDecisions([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const resp = await listDecisions(workspaceId);
      setDecisions(resp.decisions);
    } catch (err) {
      setError(describeError(err, "Erro ao carregar decisões"));
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  const execute = useCallback(
    async (decisionId: string, payload: DecisionExecutePayload = {}) => {
      if (!workspaceId) return;
      await executeDecision(workspaceId, decisionId, payload);
      await reload();
    },
    [workspaceId, reload],
  );

  const update = useCallback(
    async (decisionId: string, payload: DecisionUpdatePayload) => {
      if (!workspaceId) return;
      await updateDecision(workspaceId, decisionId, payload);
      await reload();
    },
    [workspaceId, reload],
  );

  const supersede = useCallback(
    async (oldId: string, payload: DecisionSupersedePayload) => {
      if (!workspaceId) return;
      await supersedeDecision(workspaceId, oldId, payload);
      await reload();
    },
    [workspaceId, reload],
  );

  useEffect(() => {
    void reload();
  }, [reload]);

  return { decisions, loading, error, reload, execute, update, supersede };
}
