"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  triggerPipeline,
  listPipelineRuns,
  getPipelineRun,
  cancelPipelineRun,
  listDocuments,
  listStageReviews,
  getNewDocCount,
  getLLMTier,
  getToken,
  type PipelineRunResponse,
  type PipelineEvent,
  type PipelineStageActivity,
  ApiError,
} from "@/lib/api";
import { getIFGoal } from "@/lib/api/goals";
import {
  parseStageActivityEvent,
  resolveStageName,
} from "@/lib/pipelineStageNames";
import { usePipelineWS } from "@/lib/usePipelineWS";
import { PageHeader } from "@/components/PageHeader";
import { Spinner } from "@/components/Spinner";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useWorkspace } from "@/lib/WorkspaceProvider";
import type { UserWorkspace } from "@/lib/api";

import { FailedRunCard } from "./_components/FailedRunCard";
import { ActiveRunCard } from "./_components/ActiveRunCard";
import { TriggerCard } from "./_components/TriggerCard";
import { NeedsReviewCard } from "./_components/NeedsReviewCard";
import { RunHistoryList } from "./_components/RunHistoryList";
import { useDeepLinkScroll } from "./_components/useDeepLinkScroll";
import { deriveFailedStage } from "./_components/failedStage";
import {
  getDismissedFailedRunId,
  setDismissedFailedRunId,
} from "./_components/dismissedFailedRun";
import { FreeTierSkippedBanner } from "./_components/FreeTierSkippedBanner";
import {
  getDismissedFreeTierRunId,
  setDismissedFreeTierRunId,
} from "./_components/dismissedFreeTierBanner";

const ACTIVE_STATUSES = new Set(["pending", "running", "resuming"]);

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
  /** False after initial/retry load fails — avoids showing "no ready docs" when counts are unknown. */
  const [listDataOk, setListDataOk] = useState(false);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [error, setError] = useState("");
  const [cancelOpen, setCancelOpen] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // Bumpado por QUALQUER sinal de vida do WS (eventos + heartbeats) — detecta conexão morta.
  const lastWsEventRef = useRef<number>(Date.now());
  // Bumpado SÓ por eventos de progresso (`stage_*`), não por heartbeats —
  // detecta worker travado mesmo com WS saudável.
  const lastProgressEventRef = useRef<number>(Date.now());
  // ADR-119 item 6 — timestamp do último `stage_activity` por stage.
  const lastActivityByStageRef = useRef<Record<string, number>>({});
  const [lastFailedRun, setLastFailedRun] = useState<PipelineRunResponse | null>(null);
  const [isPremium, setIsPremium] = useState(false);
  const [freeTierSkippedRun, setFreeTierSkippedRun] = useState<PipelineRunResponse | null>(null);
  const [pendingReviewCount, setPendingReviewCount] = useState<number>(0);
  const [liveStageActivity, setLiveStageActivity] =
    useState<PipelineStageActivity | null>(null);
  /** `null` enquanto carrega; `false` = sem meta IF configurada — bloqueia trigger. */
  const [hasIfGoal, setHasIfGoal] = useState<boolean | null>(null);

  const token = typeof window !== "undefined" ? getToken() : null;

  const handleWSEvent = useCallback((event: PipelineEvent) => {
    const now = Date.now();
    lastWsEventRef.current = now;
    // `usePipelineWS` filtra heartbeats antes de chamar `onEvent`, então
    // qualquer evento que chega aqui é progresso real do pipeline.
    lastProgressEventRef.current = now;

    // ADR-093 / F9.2: normaliza legacy stage IDs (E2-extratos, E1.5…)
    // que ainda chegam de emissores em pipeline/stages/*.py.
    const stage = event.stage ? resolveStageName(event.stage) : event.stage;

    const activity = parseStageActivityEvent(event);
    if (activity) {
      lastActivityByStageRef.current[activity.stage] = Date.now();
      setLiveStageActivity(activity);
    }

    if (event.event === "stage_started") {
      setLiveStageActivity((prev) =>
        prev && stage && prev.stage !== stage ? null : prev
      );
    }

    if (
      event.event === "stage_completed" ||
      event.event === "stage_skipped" ||
      event.event === "stage_failed"
    ) {
      setLiveStageActivity((prev) =>
        prev && stage && prev.stage === stage ? null : prev
      );
    }

    if (activeRun && event.run_id === activeRun.id) {
      getPipelineRun(workspace.id, activeRun.id).then((updated) => {
        setActiveRun(updated);
        setRuns((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
      }).catch(() => {});
    }
  }, [activeRun, workspace.id]);

  const handleRunFinished = useCallback((event: PipelineEvent) => {
    if (event.event === "run_completed") {
      toast.success("Relatório gerado com sucesso!", {
        action: { label: "Ver relatórios", onClick: () => router.push("/reports") },
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
      getPipelineRun(workspace.id, activeRun.id).then((updated) => {
        if (updated.status === "failed" || updated.status === "partial_failure") {
          setLastFailedRun(updated);
        }
        setActiveRun(ACTIVE_STATUSES.has(updated.status) ? updated : null);
        setRuns((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
      }).catch(() => setActiveRun(null));
    }
  }, [activeRun, router, workspace.id]);

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
    setLoading(true);
    try {
      const [runsData, docsData, tierData, newDocData, ifGoalHas] = await Promise.all([
        listPipelineRuns(workspace.id),
        listDocuments(workspace.id, ["ready", "processed"]),
        getLLMTier(workspace.id).catch((): { tier: string; has_llm_config: boolean } => ({
          tier: "free",
          has_llm_config: false,
        })),
        getNewDocCount(workspace.id).catch(() => ({ new_count: 0 })),
        getIFGoal(workspace.id)
          .then(() => true)
          .catch(() => false),
      ]);
      setListDataOk(true);
      setError("");
      setRuns(runsData.runs);
      setReadyCount(docsData.total);
      setNewCount(newDocData.new_count);
      setIsPremium(tierData.tier === "premium");
      setHasIfGoal(ifGoalHas);

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

        const recentCompleted = runsData.runs.find((r) => r.status === "completed");
        const dismissedFreeTierId = getDismissedFreeTierRunId();
        if (recentCompleted && recentCompleted.id !== dismissedFreeTierId) {
          const skipped = recentCompleted.stage_logs?.filter(
            (s) => s.status === "skipped_free_tier"
          ) ?? [];
          if (skipped.length > 0) setFreeTierSkippedRun(recentCompleted);
        }
      }
    } catch {
      setListDataOk(false);
      setError("Erro ao carregar dados");
    } finally {
      setLoading(false);
    }
  }, [workspace.id]);

  useEffect(() => {
    reload();
  }, [reload]);

  const highlightedRunId = useDeepLinkScroll(runs, loading);

  useEffect(() => {
    if (!activeRun) setLiveStageActivity(null);
  }, [activeRun]);

  // Conta revisões pendentes quando o run pausa em needs_review.
  // ADR-158 — NeedsReviewCard agora aponta para tela dedicada e exibe
  // contagem; aprovação acontece em /pipeline/runs/[id]/reviews.
  useEffect(() => {
    if (activeRun?.status !== "needs_review") {
      setPendingReviewCount(0);
      return;
    }
    let cancelled = false;
    listStageReviews(workspace.id, activeRun.id)
      .then((reviews) => {
        if (cancelled) return;
        setPendingReviewCount(reviews.filter((r) => r.status === "pending").length);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [activeRun?.id, activeRun?.status, workspace.id]);

  useEffect(() => {
    if (!activeRun || wsStatus === "connected") {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }

    async function poll() {
      if (!activeRun) return;
      try {
        const updated = await getPipelineRun(workspace.id, activeRun.id);
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
  }, [activeRun?.id, activeRun?.status, wsStatus, router, workspace.id]);

  async function handleTrigger(fromStage?: string, incremental?: boolean) {
    setError("");
    setLastFailedRun(null);
    setFreeTierSkippedRun(null);
    setTriggering(true);
    try {
      const run = await triggerPipeline(workspace.id, { from_stage: fromStage, skip_llm: !isPremium, incremental });
      setActiveRun(run);
      setRuns((prev) => [run, ...prev]);
      const now = Date.now();
      lastWsEventRef.current = now;
      lastProgressEventRef.current = now;
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao iniciar pipeline");
    } finally {
      setTriggering(false);
    }
  }

  async function handleCancel() {
    if (!activeRun) return;
    try {
      await cancelPipelineRun(workspace.id, activeRun.id);
      const updated = await getPipelineRun(workspace.id, activeRun.id);
      setActiveRun(ACTIVE_STATUSES.has(updated.status) ? updated : null);
      setRuns((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao cancelar");
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

        {!activeRun && lastFailedRun && (
          <FailedRunCard
            run={lastFailedRun}
            onRetry={() => handleTrigger()}
            onRetryFrom={(() => {
              const failedStage = deriveFailedStage(lastFailedRun);
              return failedStage ? () => handleTrigger(failedStage) : undefined;
            })()}
            onDismiss={() => {
              setDismissedFailedRunId(lastFailedRun.id);
              setLastFailedRun(null);
            }}
            triggering={triggering}
          />
        )}

        {showTrigger && (
          <TriggerCard
            readyCount={readyCount}
            newCount={newCount}
            triggering={triggering}
            listDataOk={listDataOk}
            hasIfGoal={hasIfGoal}
            onReload={() => void reload()}
            onTrigger={handleTrigger}
          />
        )}

        {activeRun && ACTIVE_STATUSES.has(activeRun.status) && (
          <ActiveRunCard
            run={activeRun}
            wsStatus={wsStatus}
            lastWsEventRef={lastWsEventRef}
            lastProgressEventRef={lastProgressEventRef}
            lastActivityByStageRef={lastActivityByStageRef}
            liveStageActivity={liveStageActivity}
            onCancel={() => setCancelOpen(true)}
          />
        )}

        {activeRun?.status === "needs_review" && (
          <NeedsReviewCard
            runId={activeRun.id}
            pausedAtStage={activeRun.paused_at_stage}
            pendingCount={pendingReviewCount}
            onCancel={() => setCancelOpen(true)}
          />
        )}

        {activeRun?.status === "completed" && (
          <div className="mb-6 rounded-lg bg-gain/10 p-4 text-center text-sm text-gain">
            Relatório gerado com sucesso! Redirecionando...
          </div>
        )}

        {freeTierSkippedRun && (
          <FreeTierSkippedBanner
            runId={freeTierSkippedRun.id}
            skippedStageCount={
              freeTierSkippedRun.stage_logs?.filter(
                (s) => s.status === "skipped_free_tier"
              ).length ?? 0
            }
            onDismiss={() => {
              setDismissedFreeTierRunId(freeTierSkippedRun.id);
              setFreeTierSkippedRun(null);
            }}
          />
        )}

        <RunHistoryList
          runs={runs}
          activeRun={activeRun}
          lastFailedRun={lastFailedRun}
          highlightedRunId={highlightedRunId}
          triggering={triggering}
          onTrigger={handleTrigger}
        />

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
