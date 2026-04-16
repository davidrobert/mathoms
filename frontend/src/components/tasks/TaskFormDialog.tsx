"use client";

/**
 * Dialog para criar ou editar uma Task (F8.2).
 *
 * Mode `create` → POST /tasks e chama `onSaved` após sucesso.
 * Mode `edit`   → PATCH /tasks/{id} com campos editáveis (status separado).
 *
 * Campos cobertos:
 *   título, descrição, categoria, prioridade, deadline_kind, deadline_date,
 *   deadline_label, ref, parent_task_id.
 * Campos fora de escopo no MVP: related_transaction_id, related_goal_id,
 * assigned_to (serão adicionados em F8.3 quando Task↔Goal↔Transaction
 * ganhar UI dedicada).
 */

import { useEffect, useState } from "react";
import { Save, Target, X } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import {
  ApiError,
  createTask,
  getIFGoal,
  updateTask,
  type TaskCreateBody,
  type TaskDeadlineKind,
  type TaskPriority,
  type TaskResponse,
} from "@/lib/api";


const CATEGORIES = [
  "Invest",
  "Orcamento",
  "Tributario",
  "Seguros",
  "Imoveis",
  "Financeiro",
  "Plan. EUA",
  "Juridico",
  "Sucessorio",
  "Pipeline",
];

const PRIORITY_LABEL: Record<TaskPriority, string> = {
  S: "Essencial",
  R: "Recomendada",
  O: "Opcional",
};

const DEADLINE_KIND_LABEL: Record<TaskDeadlineKind, string> = {
  HARD_DATE: "Data específica",
  MONTH: "Mês/ano",
  QUARTER: "Trimestre",
  CONDITIONAL: "Condicional (texto)",
  UNSCHEDULED: "Sem prazo",
};


interface TaskFormDialogProps {
  workspaceId: string;
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
  /** Se fornecido → modo edição. */
  task?: TaskResponse | null;
}


export function TaskFormDialog({
  workspaceId,
  open,
  onClose,
  onSaved,
  task,
}: TaskFormDialogProps) {
  const isEdit = !!task;
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("Invest");
  const [priority, setPriority] = useState<TaskPriority>("R");
  const [deadlineKind, setDeadlineKind] = useState<TaskDeadlineKind>("UNSCHEDULED");
  const [deadlineDate, setDeadlineDate] = useState("");
  const [deadlineLabel, setDeadlineLabel] = useState("");
  const [ref, setRef] = useState("");

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [linkToIFGoal, setLinkToIFGoal] = useState(false);
  const [ifGoalId, setIfGoalId] = useState<string | null>(null);

  // Carrega o ID do Goal IF vigente (se existir) apenas quando o dialog abre,
  // para ativar o checkbox "Ligar à meta IF".
  useEffect(() => {
    if (!open) return;
    getIFGoal(workspaceId)
      .then((g) => setIfGoalId(g.id))
      .catch(() => setIfGoalId(null)); // 404 = sem meta → desabilita checkbox
  }, [open, workspaceId]);

  // Reset/preload quando abrir
  useEffect(() => {
    if (!open) return;
    if (task) {
      setTitle(task.title);
      setDescription(task.description ?? "");
      setCategory(task.category);
      setPriority(task.priority);
      setDeadlineKind(task.deadline_kind);
      setDeadlineDate(task.deadline_date ?? "");
      setDeadlineLabel(task.deadline_label ?? "");
      setRef(task.ref ?? "");
      setLinkToIFGoal(!!task.related_goal_id);
    } else {
      setTitle("");
      setDescription("");
      setCategory("Invest");
      setPriority("R");
      setDeadlineKind("UNSCHEDULED");
      setDeadlineDate("");
      setDeadlineLabel("");
      setRef("");
      setLinkToIFGoal(false);
    }
    setError(null);
  }, [open, task]);

  async function handleSave() {
    setSaving(true);
    setError(null);

    const payload: TaskCreateBody = {
      title: title.trim(),
      description: description.trim() || null,
      category,
      priority,
      deadline_kind: deadlineKind,
      deadline_date:
        deadlineKind === "HARD_DATE" || deadlineKind === "MONTH"
          ? deadlineDate || null
          : null,
      deadline_label: deadlineLabel.trim() || null,
      ref: ref.trim() || null,
      related_goal_id: linkToIFGoal && ifGoalId ? ifGoalId : null,
    };

    try {
      if (isEdit && task) {
        await updateTask(workspaceId, task.id, payload);
      } else {
        await createTask(workspaceId, payload);
      }
      onSaved();
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
      else setError("Erro ao salvar tarefa");
      setSaving(false);
    }
  }

  const titleValid = title.trim().length > 0;
  const dateRequired = deadlineKind === "HARD_DATE" || deadlineKind === "MONTH";
  const canSave = titleValid && (!dateRequired || !!deadlineDate) && !saving;

  return (
    <Dialog open={open} onOpenChange={(v) => !v && !saving && onClose()}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? `Editar tarefa #${task!.number}` : "Nova tarefa"}
          </DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Os campos de status são alterados pelos botões de ação no card."
              : "Defina título, categoria, prioridade e (opcional) prazo."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <Label htmlFor="tfd-title">Título *</Label>
            <Input
              id="tfd-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={500}
              className="mt-1.5"
              autoFocus
            />
          </div>

          <div>
            <Label htmlFor="tfd-description">Descrição</Label>
            <Textarea
              id="tfd-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="mt-1.5"
              placeholder="Notas, links, contexto..."
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="tfd-category">Categoria</Label>
              <Select
                value={category}
                onValueChange={(v) => v && setCategory(v)}
              >
                <SelectTrigger id="tfd-category" className="mt-1.5">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CATEGORIES.map((c) => (
                    <SelectItem key={c} value={c}>
                      {c}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="tfd-priority">Prioridade</Label>
              <Select
                value={priority}
                onValueChange={(v) => v && setPriority(v as TaskPriority)}
              >
                <SelectTrigger id="tfd-priority" className="mt-1.5">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(["S", "R", "O"] as const).map((p) => (
                    <SelectItem key={p} value={p}>
                      {PRIORITY_LABEL[p]} ({p})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="tfd-dl-kind">Tipo de prazo</Label>
              <Select
                value={deadlineKind}
                onValueChange={(v) =>
                  v && setDeadlineKind(v as TaskDeadlineKind)
                }
              >
                <SelectTrigger id="tfd-dl-kind" className="mt-1.5">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(
                    [
                      "HARD_DATE",
                      "MONTH",
                      "QUARTER",
                      "CONDITIONAL",
                      "UNSCHEDULED",
                    ] as const
                  ).map((k) => (
                    <SelectItem key={k} value={k}>
                      {DEADLINE_KIND_LABEL[k]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="tfd-dl-date">
                Data {dateRequired ? "*" : "(opcional)"}
              </Label>
              <Input
                id="tfd-dl-date"
                type="date"
                value={deadlineDate}
                onChange={(e) => setDeadlineDate(e.target.value)}
                className="mt-1.5"
                disabled={!dateRequired}
              />
            </div>
          </div>

          {(deadlineKind === "QUARTER" ||
            deadlineKind === "CONDITIONAL" ||
            deadlineKind === "MONTH") && (
            <div>
              <Label htmlFor="tfd-dl-label">
                Rótulo do prazo (ex: T3/26, Antes EUA, Abr/2026)
              </Label>
              <Input
                id="tfd-dl-label"
                value={deadlineLabel}
                onChange={(e) => setDeadlineLabel(e.target.value)}
                maxLength={128}
                className="mt-1.5"
              />
            </div>
          )}

          <div>
            <Label htmlFor="tfd-ref">Referência (opcional)</Label>
            <Input
              id="tfd-ref"
              value={ref}
              onChange={(e) => setRef(e.target.value)}
              maxLength={255}
              className="mt-1.5"
              placeholder="Ex: D02, goals.json, life_plan"
            />
          </div>

          {/* Link à meta IF (F8.3) */}
          <label
            className={
              "flex cursor-pointer items-start gap-2 rounded-md border border-dashed p-3 text-sm " +
              (ifGoalId ? "hover:bg-muted/50" : "opacity-60")
            }
          >
            <input
              type="checkbox"
              checked={linkToIFGoal}
              onChange={(e) => setLinkToIFGoal(e.target.checked)}
              disabled={!ifGoalId}
              className="mt-0.5"
              aria-label="Ligar esta tarefa à meta IF"
            />
            <div className="flex-1">
              <div className="flex items-center gap-1.5 font-medium">
                <Target className="h-3.5 w-3.5" />
                Ligar à meta de Independência Financeira
              </div>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {ifGoalId
                  ? "Esta tarefa aparecerá na view da meta IF e no progresso do plano."
                  : "Configure sua meta IF primeiro em /plano para habilitar esta opção."}
              </p>
            </div>
          </label>

          {error && (
            <p className="text-sm text-destructive" role="alert">
              {error}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={onClose} disabled={saving}>
            <X className="mr-2 h-4 w-4" /> Cancelar
          </Button>
          <Button onClick={handleSave} disabled={!canSave}>
            <Save className="mr-2 h-4 w-4" />
            {saving ? "Salvando..." : isEdit ? "Salvar" : "Criar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
