"use client";

/**
 * Widget "Próximas tarefas" para o dashboard.
 * Mostra até N tasks com deadline nos próximos 7 dias + link para a rota completa.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { ListTodo, ArrowRight } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { TaskPriorityChip } from "./TaskPriorityChip";
import { TaskDeadlineBadge } from "./TaskDeadlineBadge";

import {
  listUpcomingTasks,
  ApiError,
  type TaskResponse,
} from "@/lib/api";
import { useCurrentWorkspace } from "@/lib/useCurrentWorkspace";


const MAX_ITEMS = 5;


export function UpcomingTasksWidget() {
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
        setTasks(resp.tasks.slice(0, MAX_ITEMS));
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
  }, [workspace?.id]);

  if (wsLoading || loading) {
    return (
      <Card className="p-0">
        <CardContent>
          <Skeleton className="mb-3 h-5 w-40" />
          <Skeleton className="h-4 w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="p-0">
      <CardContent>
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ListTodo className="h-4 w-4 text-muted-foreground" />
            <h2 className="text-sm font-semibold">Próximas 7 dias</h2>
            {tasks.length > 0 && (
              <span className="text-xs text-muted-foreground tabular-nums">
                ({tasks.length})
              </span>
            )}
          </div>
          <Button
            variant="ghost"
            size="xs"
            nativeButton={false}
            render={<Link href="/plano-de-acao" />}
          >
            Ver todas <ArrowRight className="ml-1 h-3 w-3" />
          </Button>
        </div>

        {error ? (
          <p className="text-xs text-destructive">{error}</p>
        ) : tasks.length === 0 ? (
          <p className="text-xs text-muted-foreground">
            Nenhuma tarefa nos próximos 7 dias.
          </p>
        ) : (
          <ul className="space-y-2">
            {tasks.map((task) => (
              <li
                key={task.id}
                className="flex items-start gap-2 text-sm"
              >
                <span className="mt-0.5 font-mono text-xs tabular-nums text-muted-foreground">
                  #{task.number}
                </span>
                <div className="flex-1">
                  <p className="truncate">{task.title}</p>
                  <div className="mt-1 flex items-center gap-2">
                    <TaskPriorityChip priority={task.priority} />
                    <TaskDeadlineBadge task={task} />
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
