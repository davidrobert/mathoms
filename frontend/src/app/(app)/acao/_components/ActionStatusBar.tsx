"use client";

import { CheckCircle2, Lightbulb, ListTodo } from "lucide-react";

import { useDecisions } from "@/hooks/useDecisions";
import { useUpcomingTasks } from "@/components/tasks/useUpcomingTasks";

import { useSuggestionsCount } from "../../plano/_components/useSuggestionsCount";

interface ActionStatusBarProps {
  workspaceId: string;
}

/** Direção E · Onda 6 — barra de status no topo de /acao.
 *
 * Mostra contadores agregados que dão escala do que está em jogo:
 * sugestões pendentes (do último relatório), tarefas com prazo nos
 * próximos 7 dias, decisões já decididas aguardando execução.
 *
 * Cada chip é clicável e leva à tab respectiva (futuro: deep-link
 * com `?tab=`). Por agora, é informativo.
 */
export function ActionStatusBar({ workspaceId }: ActionStatusBarProps) {
  const { count: suggestions } = useSuggestionsCount(workspaceId);
  const { tasks: upcoming } = useUpcomingTasks(20);
  const { decisions } = useDecisions(workspaceId);
  const decisionsToExecute = decisions.filter((d) => d.status === "Decidido")
    .length;

  return (
    <div
      role="status"
      aria-label="Resumo de itens em ação"
      className="mb-6 flex flex-wrap items-center gap-4 rounded-lg border border-border bg-muted/30 px-4 py-2.5 text-sm"
    >
      <StatusChip
        icon={Lightbulb}
        label="Sugestões pendentes"
        value={suggestions}
        muted={suggestions === 0}
      />
      <span aria-hidden className="h-4 w-px bg-border" />
      <StatusChip
        icon={ListTodo}
        label="Tarefas — próximos 7 dias"
        value={upcoming.length}
        muted={upcoming.length === 0}
      />
      <span aria-hidden className="h-4 w-px bg-border" />
      <StatusChip
        icon={CheckCircle2}
        label="Decisões a executar"
        value={decisionsToExecute}
        muted={decisionsToExecute === 0}
      />
    </div>
  );
}

interface StatusChipProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number;
  muted: boolean;
}

function StatusChip({ icon: Icon, label, value, muted }: StatusChipProps) {
  return (
    <span
      className={[
        "inline-flex items-center gap-1.5",
        muted ? "text-muted-foreground" : "text-foreground",
      ].join(" ")}
    >
      <Icon className="h-3.5 w-3.5" />
      <span className="font-mono tabular-nums font-medium">{value}</span>
      <span className="text-xs">{label}</span>
    </span>
  );
}
