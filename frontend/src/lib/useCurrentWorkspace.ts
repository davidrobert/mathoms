"use client";

/**
 * Hook standalone que resolve o workspace "corrente" do usuário (F8).
 *
 * @deprecated Para pages sob `(app)/`, preferir `useWorkspace()` de
 * `WorkspaceProvider.tsx` — resolve o workspace uma vez no layout e
 * compartilha via context, evitando N fetches duplicados.
 *
 * Este hook permanece útil para componentes fora do provider tree
 * (ex: modais, páginas de convite, contextos de teste).
 *
 * Estratégia:
 *   1. Busca /me/workspaces (lista de memberships)
 *   2. Seleciona o primeiro (ordenado por joined_at asc — workspace primário)
 *   3. Persiste no localStorage para leituras subsequentes
 */

import { useEffect, useState } from "react";
import { listMyWorkspaces, type UserWorkspace } from "./api";

const STORAGE_KEY = "fin.currentWorkspaceId";

interface UseCurrentWorkspaceResult {
  workspace: UserWorkspace | null;
  workspaces: UserWorkspace[];
  isLoading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
}

function readStoredWorkspaceId(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(STORAGE_KEY);
}

function persistWorkspaceId(id: string) {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(STORAGE_KEY, id);
  }
}

function resolveSelected(list: UserWorkspace[]): UserWorkspace | null {
  if (list.length === 0) return null;
  const storedId = readStoredWorkspaceId();
  const selected = list.find((w) => w.id === storedId) ?? list[0];
  persistWorkspaceId(selected.id);
  return selected;
}

export function useCurrentWorkspace(): UseCurrentWorkspaceResult {
  const [workspaces, setWorkspaces] = useState<UserWorkspace[]>([]);
  const [workspace, setWorkspace] = useState<UserWorkspace | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  async function load() {
    setIsLoading(true);
    setError(null);
    try {
      const { workspaces: list } = await listMyWorkspaces();
      setWorkspaces(list);
      setWorkspace(resolveSelected(list));
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { workspace, workspaces, isLoading, error, refresh: load };
}
