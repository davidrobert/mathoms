"use client";

/**
 * Card de progresso mensal de execução da tarefa (ADR-074 §F8.3).
 *
 * Consulta /tasks/{id}/progress. Se `is_trackable=false`, não renderiza
 * nada (task binária).
 */

import { useEffect, useState } from "react";
import { TrendingUp } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/format";
import {
  getTaskProgress,
  ApiError,
  type TaskProgress,
} from "@/lib/api";


interface TaskProgressCardProps {
  workspaceId: string;
  taskId: string;
}


export function TaskProgressCard({ workspaceId, taskId }: TaskProgressCardProps) {
  const [progress, setProgress] = useState<TaskProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getTaskProgress(workspaceId, taskId)
      .then((p) => {
        if (!cancelled) setProgress(p);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError) setError(err.detail);
        else setError("Erro ao carregar progresso");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [workspaceId, taskId]);

  if (loading) {
    return (
      <div className="space-y-2 rounded-lg border p-3">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-2 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <p className="text-xs text-muted-foreground">
        Progresso indisponível ({error})
      </p>
    );
  }

  if (!progress || !progress.is_trackable) {
    return null; // task não-rastreável → sem card
  }

  const pct = progress.percent_executed;
  const capped = pct != null ? Math.min(Math.max(pct, 0), 100) : null;
  const done = pct != null && pct >= 100;

  return (
    <div
      className={cn(
        "space-y-2 rounded-lg border p-3",
        done && "border-emerald-300 bg-emerald-50/30 dark:bg-emerald-950/10"
      )}
    >
      <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
        <TrendingUp className="h-3 w-3" />
        Execução no mês
      </div>

      {progress.target_brl != null && progress.executed_brl != null ? (
        <>
          <div className="flex items-baseline justify-between">
            <span className="text-sm font-semibold tabular-nums">
              {formatCurrency(progress.executed_brl)}
              <span className="text-xs font-normal text-muted-foreground">
                {" "}
                / {formatCurrency(progress.target_brl)}
              </span>
            </span>
            {pct != null && (
              <span
                className={cn(
                  "text-xs font-medium tabular-nums",
                  done ? "text-emerald-600 dark:text-emerald-400" : "text-muted-foreground"
                )}
              >
                {pct.toFixed(1)}%
              </span>
            )}
          </div>
          {capped != null && (
            <div className="h-1.5 overflow-hidden rounded-full bg-muted">
              <div
                className={cn(
                  "h-full rounded-full transition-all",
                  done ? "bg-emerald-500" : "bg-primary"
                )}
                style={{ width: `${capped}%` }}
              />
            </div>
          )}
        </>
      ) : (
        <p className="text-xs text-muted-foreground">
          Não foi possível extrair valor-alvo do título.
        </p>
      )}

      <div className="flex items-center justify-between text-[11px] text-muted-foreground">
        <span>
          {progress.matched_transactions_count} transação
          {progress.matched_transactions_count !== 1 ? "ões" : ""} no mês
        </span>
        {progress.period_end && (
          <span>
            até {new Date(progress.period_end).toLocaleDateString("pt-BR")}
          </span>
        )}
      </div>
    </div>
  );
}
