import { CheckCircle2, CircleDashed, Circle, XCircle, Lock } from "lucide-react";
import { cn } from "@/lib/utils";
import type { TaskStatus } from "@/lib/api";

const LABEL: Record<TaskStatus, string> = {
  pending: "Pendente",
  in_progress: "Em andamento",
  done: "Feito",
  cancelled: "Cancelado",
  blocked: "Bloqueado",
};

const ICON = {
  pending: Circle,
  in_progress: CircleDashed,
  done: CheckCircle2,
  cancelled: XCircle,
  blocked: Lock,
};

const COLOR: Record<TaskStatus, string> = {
  pending: "text-muted-foreground",
  in_progress: "text-blue-600 dark:text-blue-400",
  done: "text-emerald-600 dark:text-emerald-400",
  cancelled: "text-muted-foreground line-through",
  blocked: "text-amber-600 dark:text-amber-400",
};

export function TaskStatusPill({
  status,
  className,
}: {
  status: TaskStatus;
  className?: string;
}) {
  const Icon = ICON[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-xs font-medium",
        COLOR[status],
        className
      )}
      aria-label={`Status: ${LABEL[status]}`}
    >
      <Icon className="h-3.5 w-3.5" aria-hidden="true" />
      {LABEL[status]}
    </span>
  );
}
