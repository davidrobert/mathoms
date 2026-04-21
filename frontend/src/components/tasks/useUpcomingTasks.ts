"use client";

import { useEffect, useState } from "react";
import { listUpcomingTasks, ApiError, type TaskResponse } from "@/lib/api";
import { useCurrentWorkspace } from "@/lib/useCurrentWorkspace";

export interface UpcomingTasksState {
  tasks: TaskResponse[];
  loading: boolean;
  error: string | null;
}

export function useUpcomingTasks(maxItems: number): UpcomingTasksState {
  const { workspace, isLoading: wsLoading } = useCurrentWorkspace();
  const [tasks, setTasks] = useState<TaskResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!workspace?.id) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    listUpcomingTasks(workspace.id, 7)
      .then((resp) => {
        if (cancelled) return;
        setTasks(resp.tasks.slice(0, maxItems));
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiError) setError(err.detail);
        else setError("Erro ao carregar tarefas próximas");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [workspace?.id, maxItems]);

  return { tasks, loading: wsLoading || loading, error };
}
