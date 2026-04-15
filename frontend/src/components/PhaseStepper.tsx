"use client";

import { cn } from "@/lib/utils";
import type { PhaseState } from "@/lib/pipelinePhases";
import { Check, AlertTriangle, XCircle, Loader2 } from "lucide-react";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";

interface PhaseStepperProps {
  states: readonly PhaseState[];
  className?: string;
}

/**
 * Stepper horizontal de 4 fases narrativas (ADR-068).
 *
 * Mostra progresso macro ao usuário sem expor códigos internos de etapa.
 * Cada nó tem tooltip com descrição educativa da fase.
 */
export function PhaseStepper({ states, className }: PhaseStepperProps) {
  return (
    <ol
      className={cn(
        "flex w-full items-start gap-1 sm:gap-2",
        className,
      )}
      aria-label="Progresso do processamento"
    >
      {states.map((state, i) => {
        const isLast = i === states.length - 1;
        return (
          <li
            key={state.phase.id}
            className="flex min-w-0 flex-1 items-start gap-1 sm:gap-2"
          >
            <PhaseNode state={state} />
            {!isLast && <PhaseConnector state={state} />}
          </li>
        );
      })}
    </ol>
  );
}

function PhaseNode({ state }: { state: PhaseState }) {
  const { phase, status, completedStages, totalStages } = state;

  const icon = statusIcon(status, phase.order);
  const nodeClasses = cn(
    "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-xs font-medium transition-colors",
    status === "completed" && "border-gain bg-gain text-primary-foreground",
    status === "active" && "border-primary bg-primary/10 text-primary",
    status === "needs_review" && "border-warning bg-warning/10 text-warning",
    status === "failed" && "border-loss bg-loss/10 text-loss",
    status === "pending" && "border-border bg-muted text-muted-foreground",
  );

  const labelClasses = cn(
    "mt-1 text-xs leading-tight transition-colors",
    status === "active" && "font-medium text-foreground",
    status === "completed" && "text-muted-foreground",
    status === "needs_review" && "font-medium text-warning",
    status === "failed" && "font-medium text-loss",
    status === "pending" && "text-muted-foreground",
  );

  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <div className="flex min-w-0 flex-1 flex-col items-center text-center cursor-default" />
        }
      >
        <div
          className={nodeClasses}
          aria-current={status === "active" ? "step" : undefined}
        >
          {icon}
        </div>
        <span className={labelClasses}>{phase.title}</span>
        {totalStages > 0 && status === "active" && (
          <span className="text-[10px] text-muted-foreground">
            {completedStages}/{totalStages}
          </span>
        )}
      </TooltipTrigger>
      <TooltipContent className="max-w-xs">
        <div className="text-xs">
          <div className="font-medium mb-1">{phase.title}</div>
          <div className="text-muted-foreground">{phase.description}</div>
        </div>
      </TooltipContent>
    </Tooltip>
  );
}

function PhaseConnector({ state }: { state: PhaseState }) {
  const color =
    state.status === "completed"
      ? "bg-gain"
      : state.status === "active"
        ? "bg-gradient-to-r from-primary to-border"
        : state.status === "failed"
          ? "bg-loss/40"
          : "bg-border";

  return (
    <div
      className={cn(
        "mt-4 h-0.5 flex-1 rounded-full transition-colors",
        color,
      )}
      aria-hidden="true"
    />
  );
}

function statusIcon(
  status: PhaseState["status"],
  order: number,
): React.ReactNode {
  switch (status) {
    case "completed":
      return <Check className="h-4 w-4" strokeWidth={3} />;
    case "active":
      return <Loader2 className="h-4 w-4 animate-spin" />;
    case "failed":
      return <XCircle className="h-4 w-4" />;
    case "needs_review":
      return <AlertTriangle className="h-4 w-4" />;
    case "pending":
    default:
      return <span>{order}</span>;
  }
}
