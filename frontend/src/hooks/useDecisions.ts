"use client";

// A7.2a · ADR-136 — hook do aggregate Decision.
// Carrega a lista do workspace, expõe ações de mutação que invalidam
// (refetch) ao concluir. Padrão minimal — sem cache global; cada consumer
// pode adotar SWR/React Query depois se houver demanda.

import { useCallback, useEffect, useState } from "react";

import {
  ApiError,
  createDecision,
  type Decision,
  type DecisionCreatePayload,
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
  create: (payload: DecisionCreatePayload) => Promise<Decision>;
  execute: (decisionId: string, payload?: DecisionExecutePayload) => Promise<void>;
  update: (decisionId: string, payload: DecisionUpdatePayload) => Promise<void>;
  supersede: (oldId: string, payload: DecisionSupersedePayload) => Promise<void>;
}

type Reload = () => Promise<void>;

function describeError(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.detail : fallback;
}

export function useDecisions(workspaceId: string | undefined): UseDecisionsState {
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const reload = useDecisionsReload({
    workspaceId,
    setDecisions,
    setLoading,
    setError,
  });

  const mutators = useDecisionMutators(workspaceId, reload);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { decisions, loading, error, reload, ...mutators };
}

interface ReloadDeps {
  workspaceId: string | undefined;
  setDecisions: (d: Decision[]) => void;
  setLoading: (b: boolean) => void;
  setError: (s: string) => void;
}

function useDecisionsReload({
  workspaceId,
  setDecisions,
  setLoading,
  setError,
}: ReloadDeps): Reload {
  return useCallback(async () => {
    if (!workspaceId) {
      setDecisions([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const resp = await listDecisions(workspaceId);
      setDecisions(Array.isArray(resp?.decisions) ? resp.decisions : []);
    } catch (err) {
      setError(describeError(err, "Erro ao carregar decisões"));
    } finally {
      setLoading(false);
    }
  }, [workspaceId, setDecisions, setLoading, setError]);
}

interface DecisionMutators {
  create: UseDecisionsState["create"];
  execute: UseDecisionsState["execute"];
  update: UseDecisionsState["update"];
  supersede: UseDecisionsState["supersede"];
}

function useDecisionMutators(
  workspaceId: string | undefined,
  reload: Reload,
): DecisionMutators {
  return {
    create: useCreate(workspaceId, reload),
    execute: useExecute(workspaceId, reload),
    update: useUpdate(workspaceId, reload),
    supersede: useSupersede(workspaceId, reload),
  };
}

function useCreate(workspaceId: string | undefined, reload: Reload) {
  return useCallback(
    async (payload: DecisionCreatePayload): Promise<Decision> => {
      if (!workspaceId) throw new Error("Workspace não selecionado");
      const created = await createDecision(workspaceId, payload);
      await reload();
      return created;
    },
    [workspaceId, reload],
  );
}

function useExecute(workspaceId: string | undefined, reload: Reload) {
  return useCallback(
    async (decisionId: string, payload: DecisionExecutePayload = {}) => {
      if (!workspaceId) return;
      await executeDecision(workspaceId, decisionId, payload);
      await reload();
    },
    [workspaceId, reload],
  );
}

function useUpdate(workspaceId: string | undefined, reload: Reload) {
  return useCallback(
    async (decisionId: string, payload: DecisionUpdatePayload) => {
      if (!workspaceId) return;
      await updateDecision(workspaceId, decisionId, payload);
      await reload();
    },
    [workspaceId, reload],
  );
}

function useSupersede(workspaceId: string | undefined, reload: Reload) {
  return useCallback(
    async (oldId: string, payload: DecisionSupersedePayload) => {
      if (!workspaceId) return;
      await supersedeDecision(workspaceId, oldId, payload);
      await reload();
    },
    [workspaceId, reload],
  );
}
