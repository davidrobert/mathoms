"use client";

/**
 * /plano-de-acao — gestão do backlog de tarefas (ADR-074, F8.2).
 *
 * 3 views (toggle): Por prioridade (S/R/O) · Por prazo (vencem/este mês/depois) · Por categoria.
 * Actions rápidas no card: in_progress/done/reopen/cancel.
 * Drawer com detalhe completo (em componente separado).
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ListFilter, Plus, Sparkles } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { TaskCard } from "@/components/tasks/TaskCard";
import { TaskDrawer } from "@/components/tasks/TaskDrawer";
import { TaskFormDialog } from "@/components/tasks/TaskFormDialog";

import { useWorkspace } from "@/lib/WorkspaceProvider";
import {
  listTasks,
  listTaskSuggestions,
  transitionTaskStatus,
  ApiError,
  type TaskResponse,
} from "@/lib/api";

type ViewMode = "priority" | "deadline" | "category";


export default function PlanoDeAcaoPage() {
  const { workspace, isLoading: wsLoading } = useWorkspace();
  const [tasks, setTasks] = useState<TaskResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<ViewMode>("priority");
  const [includeDone, setIncludeDone] = useState(false);
  const [selectedTask, setSelectedTask] = useState<TaskResponse | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [pendingSuggestions, setPendingSuggestions] = useState(0);

  const reload = useCallback(async () => {
    if (!workspace?.id) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await listTasks(workspace.id, { include_done: includeDone });
      setTasks(resp.tasks);
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
      else setError("Erro ao carregar tarefas");
    } finally {
      setLoading(false);
    }
  }, [workspace?.id, includeDone]);

  useEffect(() => {
    reload();
  }, [reload]);

  // Contador de sugestões pendentes — refrescado junto com a lista
  useEffect(() => {
    if (!workspace?.id) return;
    let cancelled = false;
    listTaskSuggestions(workspace.id, "pending")
      .then((resp) => {
        if (!cancelled) setPendingSuggestions(resp.total);
      })
      .catch(() => {
        /* silencioso — badge não é crítico */
      });
    return () => {
      cancelled = true;
    };
  }, [workspace?.id, tasks.length]);

  async function handleStatusChange(task: TaskResponse, newStatus: "in_progress" | "done" | "pending" | "cancelled") {
    if (!workspace?.id) return;
    try {
      await transitionTaskStatus(workspace.id, task.id, newStatus);
      await reload();
    } catch (err) {
      if (err instanceof ApiError) alert(err.detail);  // simples; pode ser toast
      else alert("Erro ao atualizar status");
    }
  }

  // Detecta bloqueio por dependência: se task.parent_task_id aponta para uma
  // task ainda pending/in_progress/blocked neste mesmo workspace.
  const blockedInfo = useMemo(() => {
    const map = new Map<string, TaskResponse>();
    tasks.forEach((t) => map.set(t.id, t));
    const result = new Map<string, { isBlocked: boolean; parentNumber?: number }>();
    tasks.forEach((t) => {
      if (!t.parent_task_id) {
        result.set(t.id, { isBlocked: false });
        return;
      }
      const parent = map.get(t.parent_task_id);
      if (!parent) {
        result.set(t.id, { isBlocked: false });
        return;
      }
      const blocked = !["done", "cancelled"].includes(parent.status);
      result.set(t.id, { isBlocked: blocked, parentNumber: parent.number });
    });
    return result;
  }, [tasks]);

  const groups = useMemo(() => groupTasks(tasks, view), [tasks, view]);

  if (wsLoading || (workspace?.id && loading)) {
    return (
      <div className="mx-auto max-w-5xl px-6 py-8">
        <PageHeader title="Plano de Ação" description="Carregando..." />
        <Skeleton className="h-40" />
      </div>
    );
  }

  if (!workspace) {
    return (
      <div className="mx-auto max-w-5xl px-6 py-8">
        <PageHeader title="Plano de Ação" />
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            Nenhum workspace encontrado.
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <PageHeader
        title="Plano de Ação"
        description="Backlog gerenciável — marque feito, adie, cancele ou anexe comprovantes"
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              nativeButton={false}
              render={<Link href="/plano-de-acao/sugestoes" />}
            >
              <Sparkles className="mr-1.5 h-3.5 w-3.5" />
              Sugestões
              {pendingSuggestions > 0 && (
                <Badge variant="default" className="ml-1.5">
                  {pendingSuggestions}
                </Badge>
              )}
            </Button>
            <Button
              variant={includeDone ? "default" : "outline"}
              size="sm"
              onClick={() => setIncludeDone((v) => !v)}
            >
              <ListFilter className="mr-1.5 h-3.5 w-3.5" />
              {includeDone ? "Ocultar concluídas" : "Mostrar concluídas"}
            </Button>
            <Button size="sm" onClick={() => setCreateOpen(true)}>
              <Plus className="mr-1.5 h-3.5 w-3.5" />
              Nova
            </Button>
          </div>
        }
      />

      {/* View toggle */}
      <div className="mb-6 flex gap-1 rounded-lg bg-muted p-1 text-sm">
        {(["priority", "deadline", "category"] as const).map((v) => (
          <button
            key={v}
            type="button"
            onClick={() => setView(v)}
            className={
              "flex-1 rounded px-3 py-1.5 transition " +
              (view === v
                ? "bg-background font-medium shadow-sm"
                : "text-muted-foreground hover:text-foreground")
            }
          >
            {VIEW_LABEL[v]}
          </button>
        ))}
      </div>

      {error && (
        <Card className="mb-6 border-destructive/40">
          <CardContent className="py-4 text-sm text-destructive">
            {error}
          </CardContent>
        </Card>
      )}

      {tasks.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            Nenhuma tarefa {includeDone ? "" : "ativa "}no momento.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {groups.map(({ label, tasks: groupTasks_ }) => (
            <section key={label}>
              <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {label}
                <span className="ml-2 font-normal normal-case tabular-nums">
                  ({groupTasks_.length})
                </span>
              </h2>
              <div className="space-y-2">
                {groupTasks_.map((task) => {
                  const info = blockedInfo.get(task.id);
                  return (
                    <TaskCard
                      key={task.id}
                      task={task}
                      isBlockedByDependency={info?.isBlocked}
                      parentTaskNumber={info?.parentNumber}
                      onClick={() => setSelectedTask(task)}
                      onMarkInProgress={() => handleStatusChange(task, "in_progress")}
                      onMarkDone={() => handleStatusChange(task, "done")}
                      onReopen={() => handleStatusChange(task, "pending")}
                      onCancel={() => handleStatusChange(task, "cancelled")}
                    />
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      )}

      <TaskDrawer
        task={selectedTask}
        open={!!selectedTask}
        onClose={() => setSelectedTask(null)}
        onTaskUpdated={() => {
          reload();
          setSelectedTask(null);
        }}
      />

      <TaskFormDialog
        workspaceId={workspace.id}
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onSaved={() => {
          setCreateOpen(false);
          reload();
        }}
      />
    </div>
  );
}


// ─── Helpers ────────────────────────────────────────────────────────


const VIEW_LABEL: Record<ViewMode, string> = {
  priority: "Por prioridade",
  deadline: "Por prazo",
  category: "Por categoria",
};


const PRIORITY_GROUP_LABEL: Record<string, string> = {
  S: "Essenciais (S)",
  R: "Recomendadas (R)",
  O: "Opcionais (O)",
};


function groupTasks(
  tasks: TaskResponse[],
  view: ViewMode
): { label: string; tasks: TaskResponse[] }[] {
  if (view === "priority") {
    const order = ["S", "R", "O"] as const;
    return order
      .map((p) => ({
        label: PRIORITY_GROUP_LABEL[p],
        tasks: tasks.filter((t) => t.priority === p),
      }))
      .filter((g) => g.tasks.length > 0);
  }
  if (view === "category") {
    const byCategory = new Map<string, TaskResponse[]>();
    for (const t of tasks) {
      const arr = byCategory.get(t.category) ?? [];
      arr.push(t);
      byCategory.set(t.category, arr);
    }
    return Array.from(byCategory.entries())
      .sort(([a], [b]) => a.localeCompare(b, "pt-BR"))
      .map(([label, tasks]) => ({ label, tasks }));
  }
  // deadline: Urgente (<7d) / Este mês (<30d) / Futuro / Sem prazo
  const now = Date.now();
  const DAY = 86_400_000;
  const groups = {
    urgent: [] as TaskResponse[],
    soon: [] as TaskResponse[],
    future: [] as TaskResponse[],
    unscheduled: [] as TaskResponse[],
  };
  for (const t of tasks) {
    if (!t.deadline_date) {
      groups.unscheduled.push(t);
      continue;
    }
    const diffDays = (new Date(t.deadline_date).getTime() - now) / DAY;
    if (diffDays < 7) groups.urgent.push(t);
    else if (diffDays < 30) groups.soon.push(t);
    else groups.future.push(t);
  }
  return [
    { label: "Urgente (< 7 dias)", tasks: groups.urgent },
    { label: "Este mês (< 30 dias)", tasks: groups.soon },
    { label: "Futuro (≥ 30 dias)", tasks: groups.future },
    { label: "Sem prazo", tasks: groups.unscheduled },
  ].filter((g) => g.tasks.length > 0);
}
