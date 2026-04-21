"use client";

import { Check, Clock, RotateCcw, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import type { TaskResponse } from "@/lib/api";
import { TaskPriorityChip } from "./TaskPriorityChip";
import { TaskStatusPill } from "./TaskStatusPill";
import { TaskDeadlineBadge } from "./TaskDeadlineBadge";

interface TaskCardProps {
  task: TaskResponse;
  onClick?: () => void;
  onMarkDone?: () => void;
  onMarkInProgress?: () => void;
  onReopen?: () => void;
  onCancel?: () => void;
  isBlockedByDependency?: boolean;
  parentTaskNumber?: number;
}

export function TaskCard({
  task,
  onClick,
  onMarkDone,
  onMarkInProgress,
  onReopen,
  onCancel,
  isBlockedByDependency,
  parentTaskNumber,
}: TaskCardProps) {
  const terminal = task.status === "done" || task.status === "cancelled";

  return (
    <Card
      className={cn(
        "p-0 transition-colors",
        terminal && "opacity-60",
        isBlockedByDependency && "border-amber-300 bg-amber-50/30 dark:bg-amber-950/10"
      )}
    >
      <CardContent className="py-4">
        <div className="flex items-start justify-between gap-3">
          <button
            type="button"
            onClick={onClick}
            className="flex-1 text-left"
            aria-label={`Ver detalhes da tarefa ${task.number}`}
          >
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <span className="font-mono tabular-nums">#{task.number}</span>
              <span>·</span>
              <TaskPriorityChip priority={task.priority} />
              <Badge variant="outline">{task.category}</Badge>
              {isBlockedByDependency && parentTaskNumber && (
                <Badge variant="outline" className="border-amber-400 text-amber-700 dark:text-amber-400">
                  Bloqueada por #{parentTaskNumber}
                </Badge>
              )}
            </div>
            <h3 className={cn("mt-2 text-sm font-medium", task.status === "cancelled" && "line-through")}>
              {task.title}
            </h3>
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <TaskStatusPill status={task.status} />
              <TaskDeadlineBadge task={task} />
              {task.ref && (
                <span className="text-xs text-muted-foreground">
                  ref: {task.ref}
                </span>
              )}
            </div>
          </button>

          {/* Ações rápidas */}
          <div className="flex shrink-0 items-center gap-1">
            {task.status === "pending" && (
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label="Marcar em andamento"
                onClick={(e) => {
                  e.stopPropagation();
                  onMarkInProgress?.();
                }}
              >
                <Clock className="h-3.5 w-3.5" />
              </Button>
            )}
            {(task.status === "pending" || task.status === "in_progress") && (
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label="Marcar como feita"
                disabled={isBlockedByDependency}
                onClick={(e) => {
                  e.stopPropagation();
                  onMarkDone?.();
                }}
              >
                <Check className="h-3.5 w-3.5" />
              </Button>
            )}
            {terminal && (
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label="Reabrir"
                onClick={(e) => {
                  e.stopPropagation();
                  onReopen?.();
                }}
              >
                <RotateCcw className="h-3.5 w-3.5" />
              </Button>
            )}
            {!terminal && (
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label="Cancelar"
                onClick={(e) => {
                  e.stopPropagation();
                  onCancel?.();
                }}
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
