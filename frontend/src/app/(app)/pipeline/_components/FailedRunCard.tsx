"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, RefreshCw, XCircle } from "lucide-react";
import type { PipelineRunResponse, PipelineStageLog } from "@/lib/api";
import { formatDuration, stageName } from "@/lib/format";
import { buildUserFacingError } from "@/lib/pipelineErrorMessages";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

type OutputSummary = Record<string, unknown> | null | undefined;

function readOutputString(summary: OutputSummary, key: string): string | undefined {
  const v = summary?.[key];
  return typeof v === "string" ? v : undefined;
}

function readOutputNumber(summary: OutputSummary, key: string): number | undefined {
  const v = summary?.[key];
  return typeof v === "number" ? v : undefined;
}

function ErrorMetadataRow({ failedStage }: { failedStage: PipelineStageLog | undefined }) {
  const summary = failedStage?.output_summary as OutputSummary;
  const attempts = readOutputNumber(summary, "attempt_count");
  const errorType = readOutputString(summary, "error_type");
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 px-3 py-2 border-b border-loss/10 text-muted-foreground">
      {failedStage && (
        <span>
          <span className="text-loss/60">etapa</span>{" "}
          <span className="text-foreground">{failedStage.stage}</span>
        </span>
      )}
      {failedStage?.duration_ms != null && (
        <span>
          <span className="text-loss/60">duração</span>{" "}
          <span className="text-foreground">{(failedStage.duration_ms / 1000).toFixed(1)}s</span>
        </span>
      )}
      {attempts !== undefined && (
        <span>
          <span className="text-loss/60">tentativas</span>{" "}
          <span className="text-foreground">{attempts}</span>
        </span>
      )}
      {errorType && (
        <span>
          <span className="text-loss/60">tipo</span>{" "}
          <span className="text-foreground">{errorType}</span>
        </span>
      )}
    </div>
  );
}

function ErrorDetails({ failedStage }: { failedStage: PipelineStageLog | undefined }) {
  const summary = failedStage?.output_summary as OutputSummary;
  const traceback = readOutputString(summary, "traceback");
  return (
    <div className="mt-2 rounded-lg bg-loss/5 border border-loss/10 overflow-hidden text-xs font-mono">
      <ErrorMetadataRow failedStage={failedStage} />
      {failedStage?.errors && (
        <pre className="px-3 py-2 text-loss whitespace-pre-wrap break-all border-b border-loss/10">
          {failedStage.errors}
        </pre>
      )}
      {traceback && (
        <pre className="max-h-64 overflow-auto px-3 py-2 text-muted-foreground whitespace-pre-wrap break-all">
          {traceback}
        </pre>
      )}
    </div>
  );
}

function FailedRunHeader({
  run,
  duration,
  onDismiss,
}: {
  run: PipelineRunResponse;
  duration: number | null;
  onDismiss: () => void;
}) {
  const failedStage = run.stage_logs.find((s) => s.status === "failed");
  const userError = buildUserFacingError(failedStage?.errors, run.failed_at_stage);
  return (
    <div className="flex items-start justify-between gap-3">
      <div className="flex items-start gap-3 min-w-0">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-loss/10">
          <XCircle className="h-5 w-5 text-loss" />
        </div>
        <div className="min-w-0">
          <h2 className="font-medium text-loss">{userError.headline}</h2>
          {userError.hint && (
            <p className="text-sm text-muted-foreground mt-0.5">{userError.hint}</p>
          )}
          {duration != null && (
            <p className="text-xs text-muted-foreground mt-1">
              Falhou após {formatDuration(duration)}
            </p>
          )}
        </div>
      </div>
      <button
        onClick={onDismiss}
        className="text-muted-foreground hover:text-foreground p-1 rounded transition-colors"
        aria-label="Fechar"
      >
        <XCircle className="h-4 w-4" />
      </button>
    </div>
  );
}

export function FailedRunCard({
  run,
  onRetry,
  onRetryFrom,
  onDismiss,
  triggering,
}: {
  run: PipelineRunResponse;
  onRetry: () => void;
  onRetryFrom?: () => void;
  onDismiss: () => void;
  triggering: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const failedStage = run.stage_logs.find((s) => s.status === "failed");
  const duration = run.completed_at
    ? new Date(run.completed_at).getTime() - new Date(run.started_at).getTime()
    : null;
  const hasDetails = failedStage?.errors || failedStage?.output_summary;

  return (
    <Card id={`pipeline-run-${run.id}`} className="mb-8 border-loss/40 bg-loss/[0.03]">
      <CardContent>
        <FailedRunHeader run={run} duration={duration} onDismiss={onDismiss} />

        {hasDetails && (
          <div className="mt-3">
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1.5 text-xs font-medium text-loss hover:underline"
            >
              {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              {expanded ? "Ocultar detalhes" : "Ver detalhes técnicos"}
            </button>
            {expanded && <ErrorDetails failedStage={failedStage} />}
          </div>
        )}

        <div className="mt-4 flex gap-3">
          <Button size="sm" onClick={onRetry} disabled={triggering}>
            <RefreshCw className="mr-2 h-3.5 w-3.5" />
            {triggering ? "Iniciando..." : "Tentar novamente"}
          </Button>
          {onRetryFrom && run.failed_at_stage && (
            <Button size="sm" variant="outline" onClick={onRetryFrom} disabled={triggering}>
              Reprocessar a partir de {stageName(run.failed_at_stage)}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
