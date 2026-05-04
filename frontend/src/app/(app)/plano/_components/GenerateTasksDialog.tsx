"use client";

// ADR-162 (Onda 8 #3) — dialog de "Gerar tarefas" a partir de uma
// Decision. Pré-popula 1-3 templates baseados em `target_field`,
// permite ao usuário editar títulos antes de salvar; cada Task
// criada carrega `derived_from_decision_id`.

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  ApiError,
  createTask,
  type Decision,
  type TaskCreateBody,
} from "@/lib/api";

interface GenerateTasksDialogProps {
  workspaceId: string;
  decision: Decision;
  open: boolean;
  onOpenChange: (b: boolean) => void;
  onCreated?: () => void;
}

export function GenerateTasksDialog({
  workspaceId,
  decision,
  open,
  onOpenChange,
  onCreated,
}: GenerateTasksDialogProps) {
  const initialTemplates = useMemo(() => buildTemplates(decision), [decision]);
  const [titles, setTitles] = useState<string[]>(initialTemplates.map((t) => t.title));
  const [busy, setBusy] = useState(false);

  // Reset templates ao reabrir o dialog (decision pode mudar).
  useEffect(() => {
    setTitles(initialTemplates.map((t) => t.title));
  }, [initialTemplates]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const validTitles = titles.map((t) => t.trim()).filter(Boolean);
    if (validTitles.length === 0) {
      toast.error("Adicione pelo menos uma tarefa");
      return;
    }
    setBusy(true);
    try {
      await Promise.all(
        validTitles.map((title, idx) =>
          createTask(workspaceId, buildBody(decision, title, initialTemplates[idx])),
        ),
      );
      toast.success(
        validTitles.length === 1
          ? "1 tarefa vinculada criada"
          : `${validTitles.length} tarefas vinculadas criadas`,
      );
      onCreated?.();
      onOpenChange(false);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : "Erro ao criar tarefas");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <DialogHeader>
            <DialogTitle>Gerar tarefas para {decision.code}</DialogTitle>
            <DialogDescription>
              Cada tarefa fica vinculada a esta decisão e aparece em /acao.
              Edite os títulos abaixo antes de salvar.
            </DialogDescription>
          </DialogHeader>
          <div className="rounded-md border border-border bg-muted/30 px-3 py-2">
            <p className="text-xs font-medium">{decision.title}</p>
          </div>
          <div className="flex flex-col gap-3">
            {titles.map((value, idx) => (
              <div key={idx} className="flex flex-col gap-1.5">
                <Label className="text-xs font-medium">Tarefa {idx + 1}</Label>
                <Input
                  value={value}
                  onChange={(e) => {
                    const next = [...titles];
                    next[idx] = e.target.value;
                    setTitles(next);
                  }}
                  maxLength={500}
                />
              </div>
            ))}
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={busy}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={busy}>
              {busy ? "Criando…" : "Criar tarefas"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

interface TaskTemplate {
  title: string;
  category: string;
}

/** ADR-162 (Onda 8 #3) — templates por target_field. Se target ausente,
 * usa template genérico baseado no code da Decision. */
export function buildTemplates(decision: Decision): TaskTemplate[] {
  switch (decision.target_field) {
    case "goal.if.trs_pct":
    case "goal.if.renda_passiva_mensal_brl":
    case "goal.if.horizonte_anos":
      return [
        { title: "Atualizar planilha de Independência Financeira", category: "Plan. EUA" },
        { title: "Reler relatório com novo TRS", category: "Plan. EUA" },
      ];
    case "goal.aporte.meta_aporte_mensal_brl":
      return [
        { title: "Ajustar débito automático para nova meta de aporte", category: "Invest" },
        { title: "Revisar orçamento mensal", category: "Orcamento" },
      ];
    case "goal.dolar.meta_usd":
    case "goal.dolar.aporte_mensal_brl":
      return [
        { title: "Atualizar plano de dolarização (USD/mês)", category: "Plan. EUA" },
        { title: "Verificar custos de remessa atual", category: "Plan. EUA" },
      ];
    default:
      return [{ title: `Executar decisão ${decision.code}`, category: "Financeiro" }];
  }
}

function buildBody(
  decision: Decision,
  title: string,
  template: TaskTemplate | undefined,
): TaskCreateBody {
  return {
    title,
    description: `Derivada da decisão ${decision.code} — ${decision.title}`,
    category: template?.category ?? "Financeiro",
    priority: "R",
    deadline_kind: "UNSCHEDULED",
    derived_from_decision_id: decision.id,
  };
}
