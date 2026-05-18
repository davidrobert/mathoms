"use client";

import Link from "next/link";
import { AlertTriangle, ArrowRight, RefreshCw } from "lucide-react";
import type { PipelineRunResponse } from "@/lib/api";
import { formatDate, formatDuration, runStatusLabel, stageName } from "@/lib/format";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { deriveFailedStage } from "./failedStage";

function FailureContextLine({ run }: { run: PipelineRunResponse }) {
  const failedStage = deriveFailedStage(run);
  const isFailed = run.status === "failed" || run.status === "partial_failure";

  if (isFailed) {
    return (
      <span className="text-sm text-loss truncate">
        {failedStage
          ? `Falhou em ${stageName(failedStage)}`
          : "Falhou antes de iniciar uma etapa"}
      </span>
    );
  }
  if (run.status === "needs_review") {
    return (
      <span className="text-xs text-warning flex items-center gap-1">
        <AlertTriangle className="h-3 w-3" />
        Revisão pendente
      </span>
    );
  }
  return null;
}

function HistoryRowSummary({ run }: { run: PipelineRunResponse }) {
  const st = runStatusLabel(run.status);
  const duration = run.completed_at
    ? new Date(run.completed_at).getTime() - new Date(run.started_at).getTime()
    : null;
  return (
    <div className="flex items-center gap-3 min-w-0">
      <StatusBadge variant={st.variant}>{st.label}</StatusBadge>
      <span className="text-sm text-muted-foreground whitespace-nowrap">
        {run.stage_logs.length} etapa(s)
      </span>
      {duration != null && (
        <span className="text-xs text-muted-foreground whitespace-nowrap">
          {formatDuration(duration)}
        </span>
      )}
    </div>
  );
}

function RetryActions({
  run,
  onRetry,
  onRetryFrom,
  triggering,
}: {
  run: PipelineRunResponse;
  onRetry: () => void;
  onRetryFrom?: () => void;
  triggering: boolean;
}) {
  const failedStage = deriveFailedStage(run);
  return (
    <div className="flex gap-2 opacity-0 transition-opacity group-hover:opacity-100">
      <Button
        size="sm"
        variant="ghost"
        className="h-7 text-xs"
        onClick={onRetry}
        disabled={triggering}
      >
        <RefreshCw className="mr-1 h-3 w-3" />
        Reprocessar
      </Button>
      {onRetryFrom && failedStage && (
        <Button
          size="sm"
          variant="ghost"
          className="h-7 text-xs"
          onClick={onRetryFrom}
          disabled={triggering}
        >
          A partir de {stageName(failedStage)}
        </Button>
      )}
    </div>
  );
}

export function HistoryRow({
  run,
  highlighted,
  onRetry,
  onRetryFrom,
  triggering,
}: {
  run: PipelineRunResponse;
  highlighted?: boolean;
  onRetry: () => void;
  onRetryFrom?: () => void;
  triggering: boolean;
}) {
  const isFailed = run.status === "failed" || run.status === "partial_failure";
  const hasContextLine = isFailed || run.status === "needs_review";
  const borderClass = highlighted
    ? "border-primary ring-1 ring-primary/40"
    : isFailed
      ? "border-loss/20"
      : "border-border";

  return (
    <div
      id={`pipeline-run-${run.id}`}
      className={`group flex flex-col gap-1.5 rounded-lg border bg-card px-4 py-3 transition-colors ${borderClass}`}
    >
      <div className="flex items-center justify-between gap-3">
        <HistoryRowSummary run={run} />
        <div className="flex items-center gap-3 shrink-0">
          {isFailed && (
            <RetryActions
              run={run}
              onRetry={onRetry}
              onRetryFrom={onRetryFrom}
              triggering={triggering}
            />
          )}
          {run.status === "needs_review" && (
            <Link
              href={`/pipeline/runs/${run.id}/reviews`}
              className="inline-flex items-center gap-1 text-xs text-warning underline-offset-2 hover:underline"
            >
              Revisar
              <ArrowRight className="h-3 w-3" />
            </Link>
          )}
          {run.report_id && (
            <Link
              href={`/reports/${run.report_id}`}
              className="text-xs text-primary underline-offset-2 hover:underline opacity-0 transition-opacity group-hover:opacity-100"
            >
              Ver relatório
            </Link>
          )}
          <span className="text-sm text-muted-foreground whitespace-nowrap">
            {formatDate(run.started_at)}
          </span>
        </div>
      </div>
      {hasContextLine && (
        <div className="min-w-0">
          <FailureContextLine run={run} />
        </div>
      )}
    </div>
  );
}
