"use client";

import { useEffect, useState } from "react";
import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Clock,
  Loader2,
} from "lucide-react";
import type {
  PipelineRunResponse,
  PipelineStageActivity,
} from "@/lib/api";
import { formatDuration, formatElapsed } from "@/lib/format";
import {
  computePhaseProgress,
  computePhaseStates,
  isStageDone,
  PIPELINE_PHASES,
  getPhase,
} from "@/lib/pipelinePhases";
import { isPipelineLlmStage } from "@/lib/pipelineLlmStages";
import { PhaseStepper } from "@/components/PhaseStepper";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ConnectionChip } from "./ConnectionChip";
import { StageRow } from "./StageRow";
import { useStallWarning } from "./useStallWarning";

function useElapsedClock(startedAt: string) {
  const [elapsed, setElapsed] = useState(() => formatElapsed(startedAt));
  useEffect(() => {
    const id = setInterval(() => setElapsed(formatElapsed(startedAt)), 1000);
    return () => clearInterval(id);
  }, [startedAt]);
  return elapsed;
}

function RunHeader({
  isPending,
  title,
  subtitle,
  wsStatus,
  elapsed,
  onCancel,
}: {
  isPending: boolean;
  title: string;
  subtitle: string | null;
  wsStatus: string;
  elapsed: string;
  onCancel: () => void;
}) {
  return (
    <div className="mb-5 flex items-center justify-between">
      <div className="flex items-center gap-3">
        {isPending ? (
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        ) : (
          <div className="relative flex h-5 w-5 items-center justify-center">
            <div className="absolute h-3 w-3 animate-ping rounded-full bg-primary/30" />
            <div className="h-2.5 w-2.5 rounded-full bg-primary" />
          </div>
        )}
        <div>
          <h2 className="font-medium">{title}</h2>
          {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
        </div>
      </div>
      <div className="flex items-center gap-3">
        <ConnectionChip status={wsStatus} />
        <div className="flex shrink-0 items-center gap-1.5 whitespace-nowrap text-xs text-muted-foreground">
          <Clock className="h-3 w-3" />
          {elapsed}
        </div>
        <Button
          variant="outline"
          size="sm"
          className="text-destructive border-destructive/30 hover:bg-destructive/10"
          onClick={onCancel}
        >
          Cancelar
        </Button>
      </div>
    </div>
  );
}

function ProgressBarExplainer({ llmStageActive }: { llmStageActive: boolean }) {
  if (llmStageActive) {
    return (
      <p className="mb-2 text-[11px] leading-snug text-muted-foreground">
        Etapa com IA em andamento: a parte sólida é o que já foi concluído; a faixa ao lado com movimento
        indica processamento ativo (sem percentual fixo dentro desta etapa).
      </p>
    );
  }
  return (
    <p className="mb-2 text-[11px] leading-snug text-muted-foreground">
      O percentual só avança quando uma etapa termina. Etapas longas podem levar vários minutos sem
      mudar o número — use o tempo na lista abaixo para acompanhar a etapa atual.
    </p>
  );
}

function progressBarFillClass(status: PipelineRunResponse["status"]) {
  if (status === "failed") return "bg-loss";
  if (status === "completed") return "bg-gain";
  // `partial_failure` entregou: mesma severidade de `needs_review` (ADR-357).
  if (status === "needs_review" || status === "partial_failure") return "bg-warning";
  return "bg-primary";
}

function ProgressBar({
  status,
  pct,
  llmStageActive,
}: {
  status: PipelineRunResponse["status"];
  pct: number;
  llmStageActive: boolean;
}) {
  const fillClass = progressBarFillClass(status);
  const ariaLabel = llmStageActive
    ? `Progresso: ${pct} por cento das etapas concluídas, etapa com IA em execução`
    : `Progresso: ${pct} por cento das etapas concluídas`;

  return (
    <>
      <div className="mb-1 flex justify-between text-xs text-muted-foreground">
        <span>Progresso geral</span>
        <span>{pct}%</span>
      </div>
      <ProgressBarExplainer llmStageActive={llmStageActive} />
      <div
        className="flex h-2 w-full overflow-hidden rounded-full bg-muted"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct}
        aria-label={ariaLabel}
      >
        <div
          className={`h-full shrink-0 rounded-l-full transition-all duration-700 ease-out ${fillClass}`}
          style={{ width: `${pct}%` }}
        />
        {llmStageActive && pct < 100 ? (
          <div className="relative h-full min-w-0 flex-1 overflow-hidden rounded-r-full">
            <div className="h-full w-[42%] max-w-[min(12rem,100%)] rounded-full bg-primary/55 animate-indeterminate" />
          </div>
        ) : (
          <div className="h-full min-w-0 flex-1 bg-muted" aria-hidden />
        )}
      </div>
    </>
  );
}

function IndeterminateProgress() {
  return (
    <div className="h-2 overflow-hidden rounded-full bg-muted">
      <div className="h-full w-[40%] rounded-full bg-primary/60 animate-indeterminate" />
    </div>
  );
}

function TechnicalDetails({
  stageLogs,
  liveStageActivity,
  lastActivityByStageRef,
  completedCount,
  totalStages,
}: {
  stageLogs: PipelineRunResponse["stage_logs"];
  liveStageActivity: PipelineStageActivity | null;
  lastActivityByStageRef: React.RefObject<Record<string, number>>;
  completedCount: number;
  totalStages: number;
}) {
  const [show, setShow] = useState(false);
  return (
    <div className="mt-4">
      <button
        type="button"
        onClick={() => setShow((v) => !v)}
        className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
        aria-expanded={show}
      >
        {show ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
        {show ? "Ocultar detalhes técnicos" : `Ver detalhes técnicos (${completedCount}/${totalStages} etapas)`}
      </button>
      {show && (
        <div className="mt-3 space-y-0.5 rounded-lg border border-border/60 bg-muted/30 p-2">
          {stageLogs.map((stage) => (
            <StageRow
              key={stage.id}
              stage={stage}
              liveActivity={
                liveStageActivity?.stage === stage.stage ? liveStageActivity : undefined
              }
              lastActivityByStageRef={lastActivityByStageRef}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function resolveTitle(
  isPending: boolean,
  activePhase: ReturnType<typeof getPhase> | null,
): string {
  if (isPending) return "Iniciando processamento...";
  if (activePhase) return activePhase.title;
  return "Processando seus documentos...";
}

function resolveSubtitle(
  isPending: boolean,
  activePhase: ReturnType<typeof getPhase> | null,
  liveStageActivity: PipelineStageActivity | null,
  currentStage: string | null | undefined,
): string | null {
  if (isPending) return "Conectando ao serviço de processamento...";
  const base = activePhase?.activeMessage ?? null;

  const activityIsCurrent =
    liveStageActivity &&
    currentStage &&
    liveStageActivity.stage === currentStage;
  if (
    activityIsCurrent &&
    typeof liveStageActivity.itemsTotal === "number" &&
    liveStageActivity.itemsTotal > 0
  ) {
    const done = liveStageActivity.itemsDone ?? 0;
    const total = liveStageActivity.itemsTotal;
    const current = Math.min(done + 1, total);
    const name = liveStageActivity.currentItem ?? liveStageActivity.file;
    const counter = `Arquivo ${current}/${total}`;
    const suffix = name ? ` · ${name}` : "";
    return base ? `${base} — ${counter}${suffix}` : `${counter}${suffix}`;
  }
  return base;
}

export function ActiveRunCard({
  run,
  wsStatus,
  lastWsEventRef,
  lastProgressEventRef,
  lastActivityByStageRef,
  liveStageActivity,
  onCancel,
}: {
  run: PipelineRunResponse;
  wsStatus: string;
  lastWsEventRef: React.RefObject<number>;
  lastProgressEventRef: React.RefObject<number>;
  lastActivityByStageRef: React.RefObject<Record<string, number>>;
  liveStageActivity: PipelineStageActivity | null;
  onCancel: () => void;
}) {
  const completedCount = run.stage_logs.filter((s) => isStageDone(s.status)).length;
  const totalStages = run.stage_logs.length;
  const isPending = run.status === "pending";
  const isRunning = run.status === "running" || run.status === "resuming";
  const isActive = isPending || isRunning;
  const hasNoStages = totalStages === 0;

  // Agrupamento em 4 fases narrativas (ADR-068)
  const phaseStates = computePhaseStates(run.stage_logs, run.current_stage, run.status);
  // Progresso baseado em fases (não em sub-stages técnicos): casa com o
  // stepper "Fase N de 4" e evita 100% prematuro quando stage_logs ainda
  // não inclui a próxima etapa.
  const phasePct = computePhaseProgress(phaseStates);
  // Cap em 99% enquanto a execução está ativa — 100% só é honesto quando
  // o status efetivamente vira `completed`.
  const pct = isActive ? Math.min(99, phasePct) : phasePct;

  const elapsed = useElapsedClock(run.started_at);
  const stallWarning = useStallWarning({
    isPending,
    isRunning,
    hasNoStages,
    startedAt: run.started_at,
    lastWsEventRef,
    lastProgressEventRef,
    liveStageActivity,
    wsStatus,
  });
  const activePhase = run.current_stage
    ? getPhase(run.current_stage)
    : isPending
      ? PIPELINE_PHASES[0]
      : null;

  const title = resolveTitle(isPending, activePhase);
  const subtitle = resolveSubtitle(
    isPending,
    activePhase,
    liveStageActivity,
    run.current_stage,
  );
  const llmStageActive =
    isRunning && run.current_stage != null && isPipelineLlmStage(run.current_stage);

  return (
    <Card
      id={`pipeline-run-${run.id}`}
      className={`mb-8 ${stallWarning ? "border-alert/50" : "border-primary/30"}`}
    >
      <CardContent>
        <RunHeader
          isPending={isPending}
          title={title}
          subtitle={subtitle}
          wsStatus={wsStatus}
          elapsed={elapsed}
          onCancel={onCancel}
        />

        {stallWarning && (
          <div className="mb-4 flex items-start gap-2 rounded-lg bg-alert/10 px-3 py-2.5 text-sm text-alert">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{stallWarning}</span>
          </div>
        )}

        <div className="mb-5">
          <PhaseStepper states={phaseStates} />
        </div>

        <div className="mb-3">
          {isPending && hasNoStages ? (
            <IndeterminateProgress />
          ) : (
            <ProgressBar status={run.status} pct={pct} llmStageActive={llmStageActive} />
          )}
        </div>

        {totalStages > 0 && (
          <TechnicalDetails
            stageLogs={run.stage_logs}
            liveStageActivity={liveStageActivity}
            lastActivityByStageRef={lastActivityByStageRef}
            completedCount={completedCount}
            totalStages={totalStages}
          />
        )}

        {run.completed_at && (
          <p className="mt-3 text-xs text-muted-foreground">
            Tempo total:{" "}
            {formatDuration(
              new Date(run.completed_at).getTime() - new Date(run.started_at).getTime()
            )}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
