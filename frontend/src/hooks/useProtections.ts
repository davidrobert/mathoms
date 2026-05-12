"use client";

// A11.W5 · ADR-192 · S9-T05 — hook do aggregate Protection.
// Padrão idêntico a useDecisions/useRisks: read-list + mutators que
// invalidam (refetch) ao concluir. Sem cache global.

import { useCallback, useEffect, useState } from "react";

import {
  ApiError,
  cancelProtection,
  createProtection,
  listProtections,
  type Protection,
  type ProtectionCancelPayload,
  type ProtectionCreatePayload,
  type ProtectionUpdatePayload,
  updateProtection,
} from "@/lib/api";

export interface UseProtectionsState {
  protections: Protection[];
  loading: boolean;
  error: string;
  reload: () => Promise<void>;
  create: (payload: ProtectionCreatePayload) => Promise<Protection>;
  update: (
    protectionId: string,
    payload: ProtectionUpdatePayload,
  ) => Promise<void>;
  cancel: (
    protectionId: string,
    payload?: ProtectionCancelPayload,
  ) => Promise<void>;
}

type Reload = () => Promise<void>;

function describeError(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.detail : fallback;
}

export function useProtections(
  workspaceId: string | undefined,
): UseProtectionsState {
  const [protections, setProtections] = useState<Protection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const reload = useProtectionsReload({ workspaceId, setProtections, setLoading, setError });
  const mutators = useProtectionMutators(workspaceId, reload);
  useEffect(() => { void reload(); }, [reload]);
  return { protections, loading, error, reload, ...mutators };
}

interface ReloadDeps {
  workspaceId: string | undefined;
  setProtections: (p: Protection[]) => void;
  setLoading: (b: boolean) => void;
  setError: (s: string) => void;
}

function useProtectionsReload({
  workspaceId,
  setProtections,
  setLoading,
  setError,
}: ReloadDeps): Reload {
  return useCallback(async () => {
    if (!workspaceId) {
      setProtections([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const resp = await listProtections(workspaceId);
      setProtections(Array.isArray(resp?.protections) ? resp.protections : []);
    } catch (err) {
      setError(describeError(err, "Erro ao carregar apólices"));
    } finally {
      setLoading(false);
    }
  }, [workspaceId, setProtections, setLoading, setError]);
}

interface ProtectionMutators {
  create: UseProtectionsState["create"];
  update: UseProtectionsState["update"];
  cancel: UseProtectionsState["cancel"];
}

function useProtectionMutators(
  workspaceId: string | undefined,
  reload: Reload,
): ProtectionMutators {
  return {
    create: useCreate(workspaceId, reload),
    update: useUpdate(workspaceId, reload),
    cancel: useCancel(workspaceId, reload),
  };
}

function useCreate(workspaceId: string | undefined, reload: Reload) {
  return useCallback(
    async (payload: ProtectionCreatePayload): Promise<Protection> => {
      if (!workspaceId) throw new Error("Workspace não selecionado");
      const created = await createProtection(workspaceId, payload);
      await reload();
      return created;
    },
    [workspaceId, reload],
  );
}

function useUpdate(workspaceId: string | undefined, reload: Reload) {
  return useCallback(
    async (protectionId: string, payload: ProtectionUpdatePayload) => {
      if (!workspaceId) return;
      await updateProtection(workspaceId, protectionId, payload);
      await reload();
    },
    [workspaceId, reload],
  );
}

function useCancel(workspaceId: string | undefined, reload: Reload) {
  return useCallback(
    async (
      protectionId: string,
      payload: ProtectionCancelPayload = {},
    ) => {
      if (!workspaceId) return;
      await cancelProtection(workspaceId, protectionId, payload);
      await reload();
    },
    [workspaceId, reload],
  );
}
