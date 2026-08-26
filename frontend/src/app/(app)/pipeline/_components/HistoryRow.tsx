"use client";

import Link from "next/link";
import { AlertTriangle, ArrowRight, CircleAlert, RefreshCw } from "lucide-react";
import type { PipelineRunResponse } from "@/lib/api";
import { formatDate, formatDuration, runStatusLabel, stageName } from "@/lib/format";
import { frasePecasRetidas } from "@/lib/parecerRetencaoCopy";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { deriveFailedStage } from "./failedStage";
import { degradedRunCaveat } from "./degradedStage";
import { parecerItensRetidosNoRun } from "./parecerRetencao";

/** `partial_failure` e `needs_review` são ambos `warning` — a silhueta do ícone
 *  é o que os separa a 12px (círculo = esteja ciente; triângulo = aja agora). */
function statusIcon(status: PipelineRunResponse["status"]) {
  if (status === "partial_failure") {
    return <CircleAlert className="h-3 w-3" aria-hidden="true" />;
  }
  if (status === "needs_review") {
    return <AlertTriangle className="h-3 w-3" aria-hidden="true" />;
  }
  return undefined;
}

function RunContextLine({ run }: { run: PipelineRunResponse }) {
  if (run.status === "failed") {
    const failedStage = deriveFailedStage(run);
    return (
      <span className="text-sm text-loss truncate">
        {failedStage
          ? `Falhou em ${stageName(failedStage)}`
          : "Falhou antes de iniciar uma etapa"}
      </span>
    );
  }
  if (run.status === "partial_failure") {
    return (
      <span className="text-sm text-warning truncate">{degradedRunCaveat(run)}</span>
    );
  }
  if (run.status === "needs_review") {
    return <span className="text-xs text-warning">Revisão pendente</span>;
  }
  // A40.l22 — run que ENTREGOU o parecer com itens retidos. Fica por último:
  // `partial_failure` acima já fala do parecer que não saiu, e um run pode
  // ser as duas coisas (outro add-on degradou) — ali o caveat de degradação é
  // o sinal mais forte e a retenção parcial aparece na seção do relatório.
  const retidos = parecerItensRetidosNoRun(run);
  if (retidos > 0) {
    return (
      <span
        className="text-sm text-warning truncate"
        data-testid="history-parecer-retido"
      >
        {frasePecasRetidas(retidos)} — o parecer deste relatório está incompleto.
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
      <StatusBadge variant={st.variant} icon={statusIcon(run.status)}>
        {st.label}
      </StatusBadge>
      {/* Metadados secundários cedem espaço ao rótulo em telas estreitas. */}
      <span className="hidden min-[520px]:inline text-sm text-muted-foreground whitespace-nowrap">
        {run.stage_logs.length} etapa(s)
      </span>
      {duration != null && (
        <span className="hidden min-[520px]:inline text-xs text-muted-foreground whitespace-nowrap">
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
    // `opacity-0` não desliga hit-testing: sem `pointer-events-none` os botões
    // ficam clicáveis e invisíveis (alvo fantasma em toque).
    <div className="flex gap-2 opacity-0 pointer-events-none transition-opacity group-hover:opacity-100 group-hover:pointer-events-auto focus-within:opacity-100 focus-within:pointer-events-auto">
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
  const isFailed = run.status === "failed";
  // A40.l22 — o run com parecer parcialmente retido é `completed`: sem este
  // termo a linha de contexto existiria e nunca renderizaria (falso-verde
  // clássico — o componente pronto atrás de um gate que não abre).
  const hasContextLine =
    isFailed ||
    run.status === "partial_failure" ||
    run.status === "needs_review" ||
    parecerItensRetidosNoRun(run) > 0;
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
          {/* Ação primária de todo run que entregou — nunca atrás de hover
              (não existe hover em toque, e o foco por teclado não revelava). */}
          {run.report_id && (
            <Link
              href={`/reports/${run.report_id}`}
              className="text-xs text-primary underline-offset-2 hover:underline"
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
          <RunContextLine run={run} />
        </div>
      )}
    </div>
  );
}
