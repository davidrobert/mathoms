"use client";

/**
 * /acao Tarefas tab — gestão do backlog de tarefas (ADR-074).
 *
 * Migrado de `/plano-de-acao/page.tsx` na Onda 6 da Direção E
 * (ADR-152). 3 views (toggle): Por prioridade · Por prazo · Por
 * categoria. Actions inline: in_progress/done/reopen/cancel.
 * Drawer com detalhe completo (componente separado).
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { ListFilter, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { TaskCard } from "@/components/tasks/TaskCard";
import { TaskDrawer } from "@/components/tasks/TaskDrawer";
import { TaskFormDialog } from "@/components/tasks/TaskFormDialog";

import {
  listTasks,
  transitionTaskStatus,
  ApiError,
  type TaskResponse,
} from "@/lib/api";

interface TasksTabProps {
  workspaceId: string;
}

type ViewMode = "priority" | "deadline" | "category";

export function TasksTab({ workspaceId }: TasksTabProps) {
  const state = useTasksState(workspaceId);
  const groups = useMemo(
    () => groupTasks(state.tasks, state.view),
    [state.tasks, state.view],
  );
  const blockedInfo = useMemo(() => computeBlocked(state.tasks), [state.tasks]);

  if (state.loading) {
    return <Skeleton className="h-40" />;
  }

  return (
    <div className="flex flex-col gap-4">
      <TasksHeader state={state} />
      {state.error && <ErrorBanner message={state.error} />}
      {state.tasks.length === 0 ? (
        <EmptyState includeDone={state.includeDone} />
      ) : (
        <TasksGroups
          groups={groups}
          blockedInfo={blockedInfo}
          onSelect={state.setSelectedTask}
          onStatusChange={state.handleStatusChange}
        />
      )}
      <TaskDrawer
        task={state.selectedTask}
        open={!!state.selectedTask}
        onClose={() => state.setSelectedTask(null)}
        onTaskUpdated={() => {
          state.reload();
          state.setSelectedTask(null);
        }}
      />
      <TaskFormDialog
        workspaceId={workspaceId}
        open={state.createOpen}
        onClose={() => state.setCreateOpen(false)}
        onSaved={() => {
          state.setCreateOpen(false);
          state.reload();
        }}
      />
    </div>
  );
}

interface TasksState {
  tasks: TaskResponse[];
  loading: boolean;
  error: string | null;
  view: ViewMode;
  setView: (v: ViewMode) => void;
  includeDone: boolean;
  setIncludeDone: (b: boolean) => void;
  selectedTask: TaskResponse | null;
  setSelectedTask: (t: TaskResponse | null) => void;
  createOpen: boolean;
  setCreateOpen: (b: boolean) => void;
  reload: () => Promise<void>;
  handleStatusChange: (
    task: TaskResponse,
    newStatus: "in_progress" | "done" | "pending" | "cancelled",
  ) => Promise<void>;
}

function useTasksState(workspaceId: string): TasksState {
  const local = useTasksLocalState();
  const reload = useReloadTasks(workspaceId, local.includeDone, {
    setTasks: local.setTasks,
    setLoading: local.setLoading,
    setError: local.setError,
  });
  useEffect(() => {
    void reload();
  }, [reload]);
  const handleStatusChange = useStatusChange(workspaceId, reload);
  return { ...local, reload, handleStatusChange };
}

interface TasksLocalState {
  tasks: TaskResponse[];
  setTasks: (t: TaskResponse[]) => void;
  loading: boolean;
  setLoading: (b: boolean) => void;
  error: string | null;
  setError: (s: string | null) => void;
  view: ViewMode;
  setView: (v: ViewMode) => void;
  includeDone: boolean;
  setIncludeDone: (b: boolean) => void;
  selectedTask: TaskResponse | null;
  setSelectedTask: (t: TaskResponse | null) => void;
  createOpen: boolean;
  setCreateOpen: (b: boolean) => void;
}

function useTasksLocalState(): TasksLocalState {
  const [tasks, setTasks] = useState<TaskResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<ViewMode>("priority");
  const [includeDone, setIncludeDone] = useState(false);
  const [selectedTask, setSelectedTask] = useState<TaskResponse | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  return {
    tasks, setTasks, loading, setLoading, error, setError,
    view, setView, includeDone, setIncludeDone,
    selectedTask, setSelectedTask, createOpen, setCreateOpen,
  };
}

interface ReloadDeps {
  setTasks: (t: TaskResponse[]) => void;
  setLoading: (b: boolean) => void;
  setError: (s: string | null) => void;
}

function useReloadTasks(
  workspaceId: string,
  includeDone: boolean,
  deps: ReloadDeps,
): () => Promise<void> {
  return useCallback(async () => {
    deps.setLoading(true);
    deps.setError(null);
    try {
      const resp = await listTasks(workspaceId, { include_done: includeDone });
      deps.setTasks(resp.tasks);
    } catch (err) {
      const msg = err instanceof ApiError ? err.detail : "Erro ao carregar tarefas";
      deps.setError(msg);
    } finally {
      deps.setLoading(false);
    }
  }, [workspaceId, includeDone, deps]);
}

function useStatusChange(
  workspaceId: string,
  reload: () => Promise<void>,
): TasksState["handleStatusChange"] {
  return useCallback(
    async (task, newStatus) => {
      try {
        await transitionTaskStatus(workspaceId, task.id, newStatus);
        await reload();
      } catch (err) {
        const msg = err instanceof ApiError ? err.detail : "Erro ao atualizar status";
        alert(msg);
      }
    },
    [workspaceId, reload],
  );
}

function TasksHeader({ state }: { state: TasksState }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <ViewToggle value={state.view} onChange={state.setView} />
      <div className="flex items-center gap-2">
        <Button
          variant={state.includeDone ? "default" : "outline"}
          size="sm"
          onClick={() => state.setIncludeDone(!state.includeDone)}
        >
          <ListFilter className="mr-1.5 h-3.5 w-3.5" />
          {state.includeDone ? "Ocultar concluídas" : "Mostrar concluídas"}
        </Button>
        <Button size="sm" onClick={() => state.setCreateOpen(true)}>
          <Plus className="mr-1.5 h-3.5 w-3.5" />
          Nova
        </Button>
      </div>
    </div>
  );
}

const VIEW_LABEL: Record<ViewMode, string> = {
  priority: "Por prioridade",
  deadline: "Por prazo",
  category: "Por categoria",
};

interface ViewToggleProps {
  value: ViewMode;
  onChange: (v: ViewMode) => void;
}

function ViewToggle({ value, onChange }: ViewToggleProps) {
  return (
    <div className="flex gap-1 rounded-lg bg-muted p-1 text-sm">
      {(["priority", "deadline", "category"] as const).map((v) => (
        <button
          key={v}
          type="button"
          onClick={() => onChange(v)}
          className={
            "rounded px-3 py-1 transition " +
            (value === v
              ? "bg-background font-medium shadow-sm"
              : "text-muted-foreground hover:text-foreground")
          }
        >
          {VIEW_LABEL[v]}
        </button>
      ))}
    </div>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <Card className="border-destructive/40">
      <CardContent className="py-4 text-sm text-destructive">
        {message}
      </CardContent>
    </Card>
  );
}

function EmptyState({ includeDone }: { includeDone: boolean }) {
  return (
    <Card>
      <CardContent className="py-12 text-center text-muted-foreground">
        Nenhuma tarefa {includeDone ? "" : "ativa "}no momento.
      </CardContent>
    </Card>
  );
}

interface TasksGroupsProps {
  groups: ReturnType<typeof groupTasks>;
  blockedInfo: Map<string, { isBlocked: boolean; parentNumber?: number }>;
  onSelect: (t: TaskResponse) => void;
  onStatusChange: TasksState["handleStatusChange"];
}

function TasksGroups({
  groups,
  blockedInfo,
  onSelect,
  onStatusChange,
}: TasksGroupsProps) {
  return (
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
                  onClick={() => onSelect(task)}
                  onMarkInProgress={() => onStatusChange(task, "in_progress")}
                  onMarkDone={() => onStatusChange(task, "done")}
                  onReopen={() => onStatusChange(task, "pending")}
                  onCancel={() => onStatusChange(task, "cancelled")}
                />
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}

const PRIORITY_GROUP_LABEL: Record<string, string> = {
  S: "Essenciais (S)",
  R: "Recomendadas (R)",
  O: "Opcionais (O)",
};

function groupTasks(
  tasks: TaskResponse[],
  view: ViewMode,
): { label: string; tasks: TaskResponse[] }[] {
  if (view === "priority") return groupByPriority(tasks);
  if (view === "category") return groupByCategory(tasks);
  return groupByDeadline(tasks);
}

function groupByPriority(tasks: TaskResponse[]) {
  const order = ["S", "R", "O"] as const;
  return order
    .map((p) => ({
      label: PRIORITY_GROUP_LABEL[p],
      tasks: tasks.filter((t) => t.priority === p),
    }))
    .filter((g) => g.tasks.length > 0);
}

function groupByCategory(tasks: TaskResponse[]) {
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

type DeadlineBucket = "urgent" | "soon" | "future" | "unscheduled";

const DEADLINE_LABEL: Record<DeadlineBucket, string> = {
  urgent: "Urgente (< 7 dias)",
  soon: "Este mês (< 30 dias)",
  future: "Futuro (≥ 30 dias)",
  unscheduled: "Sem prazo",
};

function groupByDeadline(tasks: TaskResponse[]) {
  const buckets: Record<DeadlineBucket, TaskResponse[]> = {
    urgent: [], soon: [], future: [], unscheduled: [],
  };
  for (const t of tasks) buckets[deadlineBucket(t)].push(t);
  return (Object.keys(buckets) as DeadlineBucket[])
    .map((k) => ({ label: DEADLINE_LABEL[k], tasks: buckets[k] }))
    .filter((g) => g.tasks.length > 0);
}

function deadlineBucket(task: TaskResponse): DeadlineBucket {
  if (!task.deadline_date) return "unscheduled";
  const diffDays =
    (new Date(task.deadline_date).getTime() - Date.now()) / 86_400_000;
  if (diffDays < 7) return "urgent";
  if (diffDays < 30) return "soon";
  return "future";
}

function computeBlocked(
  tasks: TaskResponse[],
): Map<string, { isBlocked: boolean; parentNumber?: number }> {
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
}
