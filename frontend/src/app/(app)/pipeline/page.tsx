"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import {
  triggerPipeline,
  listPipelineRuns,
  getPipelineRun,
  cancelPipelineRun,
  resumePipelineRun,
  listDocuments,
  getNewDocCount,
  getLLMTier,
  getToken,
  type PipelineRunResponse,
  type PipelineStageLog,
  type PipelineEvent,
  type PipelineStageActivity,
  ApiError,
} from "@/lib/api";
import { usePipelineWS } from "@/lib/usePipelineWS";
import {
  formatDate,
  formatDuration,
  formatElapsed,
  runStatusLabel,
  stageStatusLabel,
  stageName,
} from "@/lib/format";
import {
  computePhaseStates,
  PIPELINE_PHASES,
  getPhase,
} from "@/lib/pipelinePhases";
import { buildUserFacingError } from "@/lib/pipelineErrorMessages";
import { isPipelineLlmStage } from "@/lib/pipelineLlmStages";
import { PageHeader } from "@/components/PageHeader";
import { PhaseStepper } from "@/components/PhaseStepper";
import { StatusBadge } from "@/components/StatusBadge";
import { Spinner } from "@/components/Spinner";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
} from "@/components/ui/tooltip";
import {
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Clock,
  Wifi,
  WifiOff,
  Loader2,
} from "lucide-react";
import { useWorkspace } from "@/lib/WorkspaceProvider";
import type { UserWorkspace } from "@/lib/api";

const ACTIVE_STATUSES = new Set(["pending", "running", "resuming"]);
const STALL_PENDING_MS = 30_000;
const STALL_RUNNING_MS = 60_000;
const DISMISSED_FAILED_RUN_KEY = "pipeline:dismissedFailedRunId";

function getDismissedFailedRunId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(DISMISSED_FAILED_RUN_KEY);
  } catch {
    return null;
  }
}

function setDismissedFailedRunId(id: string | null) {
  if (typeof window === "undefined") return;
  try {
    if (id) window.localStorage.setItem(DISMISSED_FAILED_RUN_KEY, id);
    else window.localStorage.removeItem(DISMISSED_FAILED_RUN_KEY);
  } catch {
    /* ignore */
  }
}

export default function PipelinePage() {
  const { workspace } = useWorkspace();
  if (!workspace) return null;
  return <PipelinePageContent workspace={workspace} />;
}

function PipelinePageContent({ workspace }: { workspace: UserWorkspace }) {
  const router = useRouter();
  const [runs, setRuns] = useState<PipelineRunResponse[]>([]);
  const [activeRun, setActiveRun] = useState<PipelineRunResponse | null>(null);
  const [readyCount, setReadyCount] = useState(0);
  const [newCount, setNewCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [error, setError] = useState("");
  const [cancelOpen, setCancelOpen] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastWsEventRef = useRef<number>(Date.now());
  const [lastFailedRun, setLastFailedRun] = useState<PipelineRunResponse | null>(null);
  const [isPremium, setIsPremium] = useState(false);
  const [resuming, setResuming] = useState(false);
  const [liveStageActivity, setLiveStageActivity] =
    useState<PipelineStageActivity | null>(null);

  const token = typeof window !== "undefined" ? getToken() : null;

  const handleWSEvent = useCallback((event: PipelineEvent) => {
    lastWsEventRef.current = Date.now();

    if (event.event === "stage_activity" && event.stage) {
      const d = event.detail ?? {};
      setLiveStageActivity({
        stage: event.stage,
        file: typeof d.file === "string" ? d.file : undefined,
        message: typeof d.message === "string" ? d.message : undefined,
      });
    }

    if (event.event === "stage_started") {
      setLiveStageActivity((prev) =>
        prev && event.stage && prev.stage !== event.stage ? null : prev
      );
    }

    if (
      event.event === "stage_completed" ||
      event.event === "stage_skipped" ||
      event.event === "stage_failed"
    ) {
      setLiveStageActivity((prev) =>
        prev && event.stage && prev.stage === event.stage ? null : prev
      );
    }

    if (activeRun && event.run_id === activeRun.id) {
      getPipelineRun(workspace!.id, activeRun.id).then((updated) => {
        setActiveRun(updated);
        setRuns((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
      }).catch(() => {});
    }
  }, [activeRun]);

  const handleRunFinished = useCallback((event: PipelineEvent) => {
    if (event.event === "run_completed") {
      toast.success("Relatório gerado com sucesso!", {
        action: {
          label: "Ver relatórios",
          onClick: () => router.push("/reports"),
        },
        duration: 8000,
      });
      setTimeout(() => router.push("/reports"), 2000);
    } else if (event.event === "run_failed") {
      toast.error("Pipeline falhou", {
        description: event.error || "Verifique os detalhes da execução.",
        duration: 8000,
      });
    } else if (event.event === "run_cancelled") {
      toast.info("Pipeline cancelado", { duration: 4000 });
    }

    if (activeRun) {
      getPipelineRun(workspace!.id, activeRun.id).then((updated) => {
        if (updated.status === "failed" || updated.status === "partial_failure") {
          setLastFailedRun(updated);
        }
        setActiveRun(ACTIVE_STATUSES.has(updated.status) ? updated : null);
        setRuns((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
      }).catch(() => setActiveRun(null));
    }
  }, [activeRun, router]);

  const bumpWsLiveness = useCallback(() => {
    lastWsEventRef.current = Date.now();
  }, []);

  const { status: wsStatus } = usePipelineWS({
    runId: activeRun?.id ?? null,
    token,
    onEvent: handleWSEvent,
    onHeartbeat: bumpWsLiveness,
    onRunFinished: handleRunFinished,
  });

  const reload = useCallback(async () => {
    try {
      const [runsData, docsData, tierData, newDocData] = await Promise.all([
        listPipelineRuns(workspace!.id),
        listDocuments(workspace!.id, "ready"),
        getLLMTier(workspace!.id).catch((): { tier: string; has_llm_config: boolean } => ({
          tier: "free",
          has_llm_config: false,
        })),
        getNewDocCount(workspace!.id).catch(() => ({ new_count: 0 })),
      ]);
      setRuns(runsData.runs);
      setReadyCount(docsData.total);
      setNewCount(newDocData.new_count);
      setIsPremium(tierData.tier === "premium");

      const active = runsData.runs.find((r) => ACTIVE_STATUSES.has(r.status));
      setActiveRun(active ?? null);

      if (!active) {
        const recentFailed = runsData.runs.find(
          (r) => r.status === "failed" || r.status === "partial_failure"
        );
        const dismissedId = getDismissedFailedRunId();
        if (recentFailed && recentFailed.id !== dismissedId) {
          setLastFailedRun(recentFailed);
        } else if (!recentFailed && dismissedId) {
          // No more failed runs — clear stale dismissal.
          setDismissedFailedRunId(null);
        }
      }
    } catch {
      setError("Erro ao carregar dados");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  useEffect(() => {
    if (!activeRun) setLiveStageActivity(null);
  }, [activeRun]);

  useEffect(() => {
    if (!activeRun || wsStatus === "connected") {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }

    async function poll() {
      if (!activeRun) return;
      try {
        const updated = await getPipelineRun(workspace!.id, activeRun.id);
        setActiveRun(ACTIVE_STATUSES.has(updated.status) ? updated : null);
        setRuns((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));

        if (!ACTIVE_STATUSES.has(updated.status)) {
          if (pollRef.current) clearInterval(pollRef.current);
          if (updated.status === "failed" || updated.status === "partial_failure") {
            setLastFailedRun(updated);
          }
          if (updated.status === "completed") {
            toast.success("Relatório gerado com sucesso!");
            setTimeout(() => router.push("/reports"), 1500);
          }
        }
      } catch {
        /* ignore polling errors */
      }
    }

    pollRef.current = setInterval(poll, 2000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [activeRun?.id, activeRun?.status, wsStatus, router]);

  async function handleTrigger(fromStage?: string, incremental?: boolean) {
    setError("");
    setLastFailedRun(null);
    setTriggering(true);
    try {
      const run = await triggerPipeline(workspace!.id, { from_stage: fromStage, skip_llm: !isPremium, incremental });
      setActiveRun(run);
      setRuns((prev) => [run, ...prev]);
      lastWsEventRef.current = Date.now();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao iniciar pipeline");
    } finally {
      setTriggering(false);
    }
  }

  async function handleCancel() {
    if (!activeRun) return;
    try {
      await cancelPipelineRun(workspace!.id, activeRun.id);
      const updated = await getPipelineRun(workspace!.id, activeRun.id);
      setActiveRun(ACTIVE_STATUSES.has(updated.status) ? updated : null);
      setRuns((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
    } catch {
      setError("Erro ao cancelar");
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  const showTrigger = !activeRun && !lastFailedRun;

  return (
    <TooltipProvider>
      <div className="mx-auto max-w-4xl px-6 py-8">
        <PageHeader
          title="Pipeline"
          description="Processar documentos e gerar relatório financeiro"
        />

        {error && (
          <div className="mb-4 rounded-lg bg-loss/10 p-3 text-sm text-loss">
            {error}
            <button onClick={() => setError("")} className="ml-2 font-medium underline">fechar</button>
          </div>
        )}

        {/* Failed Run Card — prominent error with retry CTAs */}
        {!activeRun && lastFailedRun && (
          <FailedRunCard
            run={lastFailedRun}
            onRetry={() => handleTrigger()}
            onRetryFrom={lastFailedRun.failed_at_stage ? () => handleTrigger(lastFailedRun.failed_at_stage!) : undefined}
            onDismiss={() => {
              setDismissedFailedRunId(lastFailedRun.id);
              setLastFailedRun(null);
            }}
            triggering={triggering}
          />
        )}

        {/* Trigger Section */}
        {showTrigger && (
          <Card className="mb-8">
            <CardContent>
              <h2 className="mb-2 font-medium">Gerar Relatório</h2>
              {readyCount === 0 ? (
                <div className="text-sm text-muted-foreground">
                  <p>Nenhum documento pronto para processar.</p>
                  <Link href="/documents" className="mt-2 inline-block text-primary hover:underline">
                    Enviar documentos →
                  </Link>
                </div>
              ) : (
                <>
                  <p className="mb-4 text-sm text-muted-foreground">
                    <span className="font-medium text-foreground">{readyCount}</span>{" "}
                    documento(s) pronto(s) para processamento
                    {newCount > 0 && newCount < readyCount && (
                      <> · <span className="font-medium text-primary">{newCount}</span> novo(s) desde última execução</>
                    )}
                    .
                  </p>
                  <div className="flex flex-wrap gap-3">
                    {/* Primary: "Processar novos" when there are new docs and it's not the first run */}
                    {newCount > 0 && newCount < readyCount ? (
                      <>
                        <Button onClick={() => handleTrigger(undefined, true)} disabled={triggering}>
                          {triggering ? (
                            <span className="inline-flex items-center gap-2">
                              <Spinner size="sm" className="text-primary-foreground" />
                              Iniciando...
                            </span>
                          ) : (
                            `Processar ${newCount} novo(s)`
                          )}
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => handleTrigger()}
                          disabled={triggering}
                        >
                          Processar todos ({readyCount})
                        </Button>
                      </>
                    ) : (
                      <Button onClick={() => handleTrigger()} disabled={triggering}>
                        {triggering ? (
                          <span className="inline-flex items-center gap-2">
                            <Spinner size="sm" className="text-primary-foreground" />
                            Iniciando...
                          </span>
                        ) : (
                          "Processar documentos"
                        )}
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      onClick={() => handleTrigger("E3")}
                      disabled={triggering}
                    >
                      Reprocessar a partir de {stageName("E3")}
                    </Button>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        )}

        {/* Active Run Progress */}
        {activeRun && ACTIVE_STATUSES.has(activeRun.status) && (
          <ActiveRunCard
            run={activeRun}
            wsStatus={wsStatus}
            lastWsEventRef={lastWsEventRef}
            liveStageActivity={liveStageActivity}
            onCancel={() => setCancelOpen(true)}
          />
        )}

        {/* needs_review banner */}
        {activeRun?.status === "needs_review" && (
          <Card className="mb-8 border-warning/50">
            <CardContent>
              <div className="flex items-center gap-3 mb-3">
                <AlertTriangle className="h-5 w-5 text-warning" />
                <h2 className="font-medium text-warning">Aguardando sua confirmação</h2>
              </div>
              <p className="text-sm text-muted-foreground mb-3">
                Pausamos o processamento em <span className="font-medium">{getPhase(activeRun.paused_at_stage ?? "").title}</span>{" "}
                para que você aprove os resultados antes de continuar.
              </p>
              <div className="flex gap-3">
                <Button
                  size="sm"
                  onClick={async () => {
                    if (!activeRun) return;
                    setResuming(true);
                    try {
                      await resumePipelineRun(workspace!.id, activeRun.id);
                      toast.success("Pipeline retomado", { duration: 3000 });
                      await reload();
                    } catch (err) {
                      toast.error(
                        err instanceof ApiError ? err.detail : "Erro ao retomar pipeline"
                      );
                    } finally {
                      setResuming(false);
                    }
                  }}
                  disabled={resuming}
                >
                  {resuming ? (
                    <span className="inline-flex items-center gap-2">
                      <Spinner size="sm" className="text-primary-foreground" />
                      Retomando...
                    </span>
                  ) : (
                    <>
                      <RefreshCw className="mr-2 h-4 w-4" />
                      Aprovar e Continuar
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Completed Run: redirect message */}
        {activeRun?.status === "completed" && (
          <div className="mb-6 rounded-lg bg-gain/10 p-4 text-center text-sm text-gain">
            Relatório gerado com sucesso! Redirecionando...
          </div>
        )}

        {/* Run History */}
        {runs.length > 0 && (
          <div>
            <h2 className="mb-3 text-lg font-medium">Histórico</h2>
            <div className="space-y-2">
              {runs
                .filter((r) => r.id !== activeRun?.id || !ACTIVE_STATUSES.has(r.status))
                .filter((r) => r.id !== lastFailedRun?.id || activeRun != null)
                .map((run) => (
                  <HistoryRow
                    key={run.id}
                    run={run}
                    onRetry={() => handleTrigger()}
                    onRetryFrom={run.failed_at_stage ? () => handleTrigger(run.failed_at_stage!) : undefined}
                    triggering={triggering}
                  />
                ))}
            </div>
          </div>
        )}

        <ConfirmDialog
          open={cancelOpen}
          onOpenChange={setCancelOpen}
          title="Cancelar execução atual?"
          description="O pipeline será interrompido ao final da etapa em execução. Etapas já concluídas serão mantidas."
          confirmLabel="Cancelar execução"
          variant="destructive"
          onConfirm={handleCancel}
        />
      </div>
    </TooltipProvider>
  );
}

// ─── Failed Run Card ───

function FailedRunCard({
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

  // Mensagem user-facing centrada em impacto + próximo passo (ADR-068)
  const userError = buildUserFacingError(
    failedStage?.errors,
    run.failed_at_stage,
  );

  return (
    <Card className="mb-8 border-loss/40 bg-loss/[0.03]">
      <CardContent>
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 min-w-0">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-loss/10">
              <XCircle className="h-5 w-5 text-loss" />
            </div>
            <div className="min-w-0">
              <h2 className="font-medium text-loss">{userError.headline}</h2>
              {userError.hint && (
                <p className="text-sm text-muted-foreground mt-0.5">
                  {userError.hint}
                </p>
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

        {/* Error details */}
        {failedStage?.errors && (
          <div className="mt-3">
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1.5 text-xs font-medium text-loss hover:underline"
            >
              {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              {expanded ? "Ocultar detalhes" : "Ver detalhes do erro"}
            </button>
            {expanded && (
              <pre className="mt-2 max-h-48 overflow-auto rounded-lg bg-loss/5 p-3 text-xs text-loss font-mono">
                {failedStage.errors}
              </pre>
            )}
          </div>
        )}

        {/* Retry CTAs */}
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

// ─── Active Run Card ───

function ActiveRunCard({
  run,
  wsStatus,
  lastWsEventRef,
  liveStageActivity,
  onCancel,
}: {
  run: PipelineRunResponse;
  wsStatus: string;
  lastWsEventRef: React.RefObject<number>;
  liveStageActivity: PipelineStageActivity | null;
  onCancel: () => void;
}) {
  const completedCount = run.stage_logs.filter(
    (s) => s.status === "completed" || s.status === "skipped" || s.status === "skipped_free_tier"
  ).length;
  const totalStages = run.stage_logs.length;
  /** Só etapas já finalizadas — evita “80%” no início de uma etapa longa (o WS reporta % ao entrar na etapa). */
  const pct = totalStages > 0 ? Math.round((completedCount / totalStages) * 100) : 0;
  const isPending = run.status === "pending";
  const isRunning = run.status === "running" || run.status === "resuming";
  const hasNoStages = totalStages === 0;

  const [elapsed, setElapsed] = useState(() => formatElapsed(run.started_at));
  const [stallWarning, setStallWarning] = useState<string | null>(null);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => {
      setElapsed(formatElapsed(run.started_at));

      const now = Date.now();
      const runAge = now - new Date(run.started_at).getTime();
      const sinceLastWs = now - lastWsEventRef.current;

      if (isPending && hasNoStages && runAge > STALL_PENDING_MS) {
        setStallWarning(
          "O processamento está aguardando há mais de 30s. Pode haver um problema na fila de execução."
        );
      } else if (isRunning && sinceLastWs > STALL_RUNNING_MS) {
        setStallWarning(
          wsStatus === "connected"
            ? "Sem sinal do servidor há mais de 1 min. Se o indicador mostrar “Tempo real”, aguarde; caso contrário, verifique a conexão."
            : "Sem atualizações recentes. O processamento pode estar lento."
        );
      } else {
        setStallWarning(null);
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [run.started_at, isPending, isRunning, hasNoStages, lastWsEventRef, wsStatus]);

  // Agrupamento em 4 fases narrativas (ADR-068)
  const phaseStates = computePhaseStates(run.stage_logs, run.current_stage, run.status);
  const activePhase = run.current_stage
    ? getPhase(run.current_stage)
    : isPending
      ? PIPELINE_PHASES[0]
      : null;

  const title = isPending
    ? "Iniciando processamento..."
    : activePhase
      ? activePhase.title
      : "Processando seus documentos...";

  const subtitle = isPending
    ? "Conectando ao serviço de processamento..."
    : activePhase
      ? activePhase.activeMessage
      : null;

  const llmStageActive =
    isRunning &&
    run.current_stage != null &&
    isPipelineLlmStage(run.current_stage);

  return (
    <Card className={`mb-8 ${stallWarning ? "border-alert/50" : "border-primary/30"}`}>
      <CardContent>
        {/* Header */}
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
              {subtitle && (
                <p className="text-xs text-muted-foreground">{subtitle}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <ConnectionChip status={wsStatus} />
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
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

        {/* Stall Warning */}
        {stallWarning && (
          <div className="mb-4 flex items-start gap-2 rounded-lg bg-alert/10 px-3 py-2.5 text-sm text-alert">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{stallWarning}</span>
          </div>
        )}

        {/* Phase Stepper — macro view (4 fases narrativas) */}
        <div className="mb-5">
          <PhaseStepper states={phaseStates} />
        </div>

        {/* Progress Bar (quando já temos etapas logadas) */}
        <div className="mb-3">
          {isPending && hasNoStages ? (
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <div className="h-full w-[40%] rounded-full bg-primary/60 animate-indeterminate" />
            </div>
          ) : (
            <>
              <div className="mb-1 flex justify-between text-xs text-muted-foreground">
                <span>Progresso geral</span>
                <span>{pct}%</span>
              </div>
              <p className="mb-2 text-[11px] leading-snug text-muted-foreground">
                {llmStageActive ? (
                  <>
                    Etapa com IA em andamento: a parte sólida é o que já foi concluído; a faixa ao lado com movimento
                    indica processamento ativo (sem percentual fixo dentro desta etapa).
                  </>
                ) : (
                  <>
                    O percentual só avança quando uma etapa termina. Etapas longas podem levar vários minutos sem
                    mudar o número — use o tempo na lista abaixo para acompanhar a etapa atual.
                  </>
                )}
              </p>
              <div
                className="flex h-2 w-full overflow-hidden rounded-full bg-muted"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={pct}
                aria-label={
                  llmStageActive
                    ? `Progresso: ${pct} por cento das etapas concluídas, etapa com IA em execução`
                    : `Progresso: ${pct} por cento das etapas concluídas`
                }
              >
                <div
                  className={`h-full shrink-0 rounded-l-full transition-all duration-700 ease-out ${
                    run.status === "failed" || run.status === "partial_failure"
                      ? "bg-loss"
                      : run.status === "completed"
                        ? "bg-gain"
                        : run.status === "needs_review"
                          ? "bg-warning"
                          : "bg-primary"
                  }`}
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
          )}
        </div>

        {/* Disclosure: detalhes técnicos (etapas individuais) */}
        {totalStages > 0 && (
          <div className="mt-4">
            <button
              type="button"
              onClick={() => setShowTechnicalDetails((v) => !v)}
              className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
              aria-expanded={showTechnicalDetails}
            >
              {showTechnicalDetails ? (
                <ChevronUp className="h-3 w-3" />
              ) : (
                <ChevronDown className="h-3 w-3" />
              )}
              {showTechnicalDetails
                ? "Ocultar detalhes técnicos"
                : `Ver detalhes técnicos (${completedCount}/${totalStages} etapas)`}
            </button>
            {showTechnicalDetails && (
              <div className="mt-3 space-y-0.5 rounded-lg border border-border/60 bg-muted/30 p-2">
                {run.stage_logs.map((stage) => (
                  <StageRow
                    key={stage.id}
                    stage={stage}
                    liveActivity={
                      liveStageActivity?.stage === stage.stage
                        ? liveStageActivity
                        : undefined
                    }
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Elapsed Time (completed) */}
        {run.completed_at && (
          <p className="mt-3 text-xs text-muted-foreground">
            Tempo total:{" "}
            {formatDuration(
              new Date(run.completed_at).getTime() -
                new Date(run.started_at).getTime()
            )}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Connection Chip ───

function ConnectionChip({ status }: { status: string }) {
  if (status === "connected") {
    return (
      <Tooltip>
        <TooltipTrigger
          render={
            <span className="inline-flex items-center gap-1 rounded-full bg-gain/10 px-2 py-0.5 text-[10px] font-medium text-gain cursor-default" />
          }
        >
          <Wifi className="h-2.5 w-2.5" />
          Tempo real
        </TooltipTrigger>
        <TooltipContent>Conectado via WebSocket — atualizações instantâneas</TooltipContent>
      </Tooltip>
    );
  }

  if (status === "connecting") {
    return (
      <span className="inline-flex animate-pulse items-center gap-1 rounded-full bg-alert/10 px-2 py-0.5 text-[10px] font-medium text-alert">
        <Wifi className="h-2.5 w-2.5" />
        Conectando...
      </span>
    );
  }

  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground cursor-default" />
        }
      >
        <WifiOff className="h-2.5 w-2.5" />
        Polling
      </TooltipTrigger>
      <TooltipContent>Sem conexão em tempo real — atualizando a cada 2s</TooltipContent>
    </Tooltip>
  );
}

function useNowInterval(active: boolean, ms: number) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => setNow(Date.now()), ms);
    return () => clearInterval(id);
  }, [active, ms]);
  return now;
}

// ─── Stage Row ───

function StageRow({
  stage,
  liveActivity,
}: {
  stage: PipelineStageLog;
  liveActivity?: PipelineStageActivity;
}) {
  const st = stageStatusLabel(stage.status);
  const [expanded, setExpanded] = useState(false);
  const running = stage.status === "running";
  const now = useNowInterval(running, 1000);
  const displayMs = running
    ? Math.max(0, now - new Date(stage.started_at).getTime())
    : stage.duration_ms;

  const variantColors: Record<string, string> = {
    neutral: "text-muted-foreground",
    info: "text-info-financial",
    success: "text-gain",
    error: "text-loss",
    warning: "text-warning",
    muted: "text-muted-foreground",
  };

  return (
    <div>
      <div
        className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
          stage.status === "running"
            ? "bg-primary/5"
            : stage.status === "needs_review"
              ? "bg-warning/5"
              : ""
        }`}
      >
        <span className={`text-base ${variantColors[st.variant] ?? "text-muted-foreground"} ${stage.status === "running" ? "animate-pulse" : ""}`}>
          {st.icon}
        </span>
        <span className={`flex-1 ${stage.status === "running" ? "font-medium" : ""}`}>
          {stageName(stage.stage)}
          <Tooltip>
            <TooltipTrigger
              render={
                <span className="ml-2 inline-block rounded bg-muted px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground cursor-help" />
              }
            >
              {stage.stage}
            </TooltipTrigger>
            <TooltipContent>Código interno usado em logs e suporte</TooltipContent>
          </Tooltip>
          {stage.status === "running" && (
            <span className="ml-2 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
          )}
          {stage.status === "needs_review" && (
            <span className="ml-2 text-xs text-warning">(revisão)</span>
          )}
        </span>
        <span className="text-xs text-muted-foreground font-mono">
          {formatDuration(displayMs)}
        </span>
        {stage.errors && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setExpanded(!expanded)}
            className="h-auto px-1.5 py-0.5 text-xs text-loss"
          >
            {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            {expanded ? "ocultar" : "ver erro"}
          </Button>
        )}
      </div>
      {expanded && stage.errors && (
        <pre className="mx-3 mb-1 max-h-40 overflow-auto rounded bg-loss/5 p-3 text-xs text-loss font-mono">
          {stage.errors}
        </pre>
      )}
      {stage.status === "running" && liveActivity && (liveActivity.message || liveActivity.file) && (
        <div className="mx-3 mb-1 rounded-md border border-border/50 bg-muted/40 px-3 py-2 text-xs">
          {liveActivity.message && (
            <p className="text-muted-foreground leading-snug">{liveActivity.message}</p>
          )}
          {liveActivity.file && (
            <p
              className="mt-1 font-mono text-[11px] text-foreground/90 truncate"
              title={liveActivity.file}
            >
              Arquivo: {liveActivity.file}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ─── History Row ───

function HistoryRow({
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
  const st = runStatusLabel(run.status);
  const isFailed = run.status === "failed" || run.status === "partial_failure";
  const duration = run.completed_at
    ? new Date(run.completed_at).getTime() - new Date(run.started_at).getTime()
    : null;

  return (
    <div
      className={`group flex items-center justify-between rounded-lg border bg-card px-4 py-3 ${
        isFailed ? "border-loss/20" : "border-border"
      }`}
    >
      <div className="flex items-center gap-3">
        <StatusBadge variant={st.variant}>{st.label}</StatusBadge>
        <span className="text-sm text-muted-foreground">
          {run.stage_logs.length} etapa(s)
        </span>
        {run.failed_at_stage && (
          <span className="text-sm text-loss">
            Falhou em {stageName(run.failed_at_stage)}
          </span>
        )}
        {run.status === "needs_review" && (
          <span className="text-xs text-warning flex items-center gap-1">
            <AlertTriangle className="h-3 w-3" />
            Revisão pendente
          </span>
        )}
        {duration != null && (
          <span className="text-xs text-muted-foreground">{formatDuration(duration)}</span>
        )}
      </div>
      <div className="flex items-center gap-3">
        {isFailed && (
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
            {onRetryFrom && run.failed_at_stage && (
              <Button
                size="sm"
                variant="ghost"
                className="h-7 text-xs"
                onClick={onRetryFrom}
                disabled={triggering}
              >
                A partir de {stageName(run.failed_at_stage)}
              </Button>
            )}
          </div>
        )}
        <span className="text-sm text-muted-foreground">{formatDate(run.started_at)}</span>
      </div>
    </div>
  );
}
