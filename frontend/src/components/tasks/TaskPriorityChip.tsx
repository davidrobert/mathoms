import { Badge } from "@/components/ui/badge";
import type { TaskPriority } from "@/lib/api";

const LABEL: Record<TaskPriority, string> = {
  S: "Essencial",
  R: "Recomendada",
  O: "Opcional",
};

const VARIANT: Record<TaskPriority, "default" | "secondary" | "outline"> = {
  S: "default",
  R: "secondary",
  O: "outline",
};

export function TaskPriorityChip({ priority }: { priority: TaskPriority }) {
  return (
    <Badge
      variant={VARIANT[priority]}
      aria-label={`Prioridade: ${LABEL[priority]}`}
    >
      {LABEL[priority]}
    </Badge>
  );
}
