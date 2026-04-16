"use client";

/**
 * WorkspaceProvider — compartilha o workspace corrente via React Context.
 *
 * Antes (pré-P2), cada page chamava `useCurrentWorkspace()` individualmente,
 * disparando N fetches de `/me/workspaces` em paralelo. Agora o fetch
 * acontece uma vez no layout e o resultado é distribuído via context.
 *
 * Uso:
 *   // No layout:
 *   <WorkspaceProvider>{children}</WorkspaceProvider>
 *
 *   // Em qualquer page/component:
 *   const { workspace, isLoading } = useWorkspace();
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { listMyWorkspaces, type UserWorkspace } from "./api";

const STORAGE_KEY = "fin.currentWorkspaceId";

interface WorkspaceContextValue {
  workspace: UserWorkspace | null;
  workspaces: UserWorkspace[];
  isLoading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [workspaces, setWorkspaces] = useState<UserWorkspace[]>([]);
  const [workspace, setWorkspace] = useState<UserWorkspace | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const { workspaces: list } = await listMyWorkspaces();
      setWorkspaces(list);
      if (list.length === 0) {
        setWorkspace(null);
        return;
      }
      const storedId =
        typeof window !== "undefined"
          ? window.localStorage.getItem(STORAGE_KEY)
          : null;
      const selected = list.find((w) => w.id === storedId) ?? list[0];
      setWorkspace(selected);
      if (typeof window !== "undefined") {
        window.localStorage.setItem(STORAGE_KEY, selected.id);
      }
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <WorkspaceContext.Provider
      value={{ workspace, workspaces, isLoading, error, refresh: load }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}

/**
 * Hook para consumir o workspace corrente.
 *
 * Drop-in replacement para `useCurrentWorkspace()` — mesma interface,
 * mas lê do context em vez de disparar fetch próprio.
 */
export function useWorkspace(): WorkspaceContextValue {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) {
    throw new Error("useWorkspace must be used within <WorkspaceProvider>");
  }
  return ctx;
}
