import { Calendar, AlertCircle, Clock } from "lucide-react";
import { cn } from "@/lib/cn";
import type { TaskResponse } from "@/lib/api";

/** Dias entre hoje e a data (ignora timezone). */
function daysUntil(isoDate: string): number {
  const target = new Date(isoDate);
  const today = new Date();
  target.setHours(0, 0, 0, 0);
  today.setHours(0, 0, 0, 0);
  return Math.round((target.getTime() - today.getTime()) / 86_400_000);
}

function formatLabel(task: TaskResponse): string {
  if (task.deadline_kind === "UNSCHEDULED") return "Sem prazo";
  if (task.deadline_label) return task.deadline_label;
  if (task.deadline_date) {
    return new Date(task.deadline_date).toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  }
  return "—";
}

/** Cor baseada em urgência.
 *  <7d: vermelho (urgente), <30d: laranja (atenção), >=30d: neutro.
 */
function urgencyColor(task: TaskResponse): string {
  if (task.deadline_kind !== "HARD_DATE" || !task.deadline_date) {
    return "text-muted-foreground";
  }
  const d = daysUntil(task.deadline_date);
  if (d < 0) return "text-destructive font-medium";
  if (d < 7) return "text-destructive";
  if (d < 30) return "text-amber-600 dark:text-amber-400";
  return "text-muted-foreground";
}

export function TaskDeadlineBadge({
  task,
  className,
}: {
  task: TaskResponse;
  className?: string;
}) {
  const label = formatLabel(task);
  const color = urgencyColor(task);
  const isOverdue =
    task.deadline_kind === "HARD_DATE" &&
    task.deadline_date &&
    daysUntil(task.deadline_date) < 0;

  const Icon = isOverdue ? AlertCircle : task.deadline_kind === "HARD_DATE" ? Clock : Calendar;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 text-xs tabular-nums",
        color,
        className
      )}
    >
      <Icon className="h-3 w-3" aria-hidden="true" />
      {label}
    </span>
  );
}
