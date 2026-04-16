"use client";

import { useEffect, useState } from "react";

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";

import { TaskPriorityChip } from "./TaskPriorityChip";
import { TaskStatusPill } from "./TaskStatusPill";
import { TaskDeadlineBadge } from "./TaskDeadlineBadge";
import { TaskProgressCard } from "./TaskProgressCard";
import { TaskAttachments } from "./TaskAttachments";

import { useCurrentWorkspace } from "@/lib/useCurrentWorkspace";
import { updateTask, ApiError, type TaskResponse } from "@/lib/api";


interface TaskDrawerProps {
  task: TaskResponse | null;
  open: boolean;
  onClose: () => void;
  onTaskUpdated: () => void;
}


export function TaskDrawer({
  task,
  open,
  onClose,
  onTaskUpdated,
}: TaskDrawerProps) {
  const { workspace } = useCurrentWorkspace();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (!task) return;
    setTitle(task.title);
    setDescription(task.description ?? "");
    setDirty(false);
    setError(null);
  }, [task?.id, task]);

  async function handleSave() {
    if (!workspace || !task) return;
    setSaving(true);
    setError(null);
    try {
      await updateTask(workspace.id, task.id, {
        title: title.trim(),
        description: description.trim() || null,
      });
      onTaskUpdated();
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
      else setError("Erro ao salvar alterações");
      setSaving(false);
    }
  }

  return (
    <Sheet open={open} onOpenChange={(v) => !v && onClose()}>
      <SheetContent className="w-full max-w-lg overflow-y-auto">
        {task && (
          <>
            <SheetHeader>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span className="font-mono tabular-nums">#{task.number}</span>
                <span>·</span>
                <TaskPriorityChip priority={task.priority} />
                <Badge variant="outline">{task.category}</Badge>
              </div>
              <SheetTitle className="mt-1 text-base">
                {task.title}
              </SheetTitle>
              <SheetDescription className="flex items-center gap-3">
                <TaskStatusPill status={task.status} />
                <TaskDeadlineBadge task={task} />
              </SheetDescription>
            </SheetHeader>

            <div className="space-y-4 px-6 py-4">
              <div>
                <Label htmlFor="task-title">Título</Label>
                <Input
                  id="task-title"
                  value={title}
                  onChange={(e) => {
                    setTitle(e.target.value);
                    setDirty(true);
                  }}
                  className="mt-1.5"
                />
              </div>

              <div>
                <Label htmlFor="task-description">Descrição</Label>
                <Textarea
                  id="task-description"
                  value={description}
                  onChange={(e) => {
                    setDescription(e.target.value);
                    setDirty(true);
                  }}
                  rows={4}
                  className="mt-1.5"
                  placeholder="Notas, links, detalhes..."
                />
              </div>

              <Separator />

              {/* F8.3: % executado para tarefas rastreáveis (aporte mensal etc) */}
              {workspace && task.status !== "cancelled" && (
                <TaskProgressCard workspaceId={workspace.id} taskId={task.id} />
              )}

              <dl className="space-y-2 text-sm">
                {task.ref && (
                  <Row label="Referência" value={task.ref} />
                )}
                {task.deadline_label && (
                  <Row label="Prazo" value={task.deadline_label} />
                )}
                {task.parent_task_id && (
                  <Row
                    label="Depende de"
                    value={`Task com ID ${task.parent_task_id.substring(0, 8)}...`}
                  />
                )}
                {task.completed_at && (
                  <Row
                    label="Concluída em"
                    value={new Date(task.completed_at).toLocaleDateString("pt-BR")}
                  />
                )}
                {task.cancelled_at && (
                  <Row
                    label="Cancelada em"
                    value={new Date(task.cancelled_at).toLocaleDateString("pt-BR")}
                  />
                )}
                <Row
                  label="Origem"
                  value={ORIGIN_LABEL[task.created_from]}
                />
              </dl>

              {task.status_reason && (
                <>
                  <Separator />
                  <div>
                    <Label className="text-xs text-muted-foreground">
                      Motivo do status
                    </Label>
                    <p className="mt-1 text-sm">{task.status_reason}</p>
                  </div>
                </>
              )}

              <Separator />

              {/* F8.3: Anexos (comprovantes, contratos, notas) */}
              {workspace && (
                <TaskAttachments workspaceId={workspace.id} taskId={task.id} />
              )}

              {error && (
                <p className="text-sm text-destructive">{error}</p>
              )}

              <div className="flex justify-end gap-2">
                <Button
                  variant="ghost"
                  onClick={onClose}
                  disabled={saving}
                >
                  Fechar
                </Button>
                <Button
                  onClick={handleSave}
                  disabled={!dirty || saving || !title.trim()}
                >
                  {saving ? "Salvando..." : "Salvar"}
                </Button>
              </div>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}


function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-right text-sm">{value}</dd>
    </div>
  );
}


const ORIGIN_LABEL: Record<string, string> = {
  manual: "Criada manualmente",
  seed: "Importada do backlog",
  llm_suggestion: "Sugestão aprovada (LLM)",
};
