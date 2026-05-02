"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import {
  ApiError,
  getPipelineRun,
  listStageReviews,
  resumePipelineRun,
  type PipelineRunResponse,
  type StageReviewResponse,
} from "@/lib/api";

interface UseReviewListResult {
  reviews: StageReviewResponse[] | null;
  run: PipelineRunResponse | null;
  loading: boolean;
  error: string | null;
  resuming: boolean;
  reload: () => Promise<void>;
}

interface State {
  reviews: StageReviewResponse[] | null;
  run: PipelineRunResponse | null;
  loading: boolean;
  error: string | null;
  resuming: boolean;
}

const INITIAL: State = {
  reviews: null,
  run: null,
  loading: true,
  error: null,
  resuming: false,
};

/**
 * Carrega lista de reviews + run e dispara auto-resume quando todas saem de
 * pending (regra inegociável §7: backend só aceita resume com count==0).
 */
export function useReviewList(
  workspaceId: string,
  runId: string,
): UseReviewListResult {
  const router = useRouter();
  const [s, setS] = useState<State>(INITIAL);
  const reload = useReloader(workspaceId, runId, setS);
  useEffect(() => void reload(), [reload]);
  useAutoResume({ workspaceId, runId, s, setS, router });
  return { ...s, reload };
}

function useReloader(
  workspaceId: string,
  runId: string,
  setS: React.Dispatch<React.SetStateAction<State>>,
): () => Promise<void> {
  return useCallback(async () => {
    setS((p) => ({ ...p, loading: true, error: null }));
    try {
      const [reviews, run] = await Promise.all([
        listStageReviews(workspaceId, runId),
        getPipelineRun(workspaceId, runId),
      ]);
      setS((p) => ({ ...p, reviews, run, loading: false }));
    } catch (err) {
      const error = err instanceof ApiError ? err.detail : "Erro ao carregar revisões";
      setS((p) => ({ ...p, error, loading: false }));
    }
  }, [workspaceId, runId, setS]);
}

interface AutoResumeArgs {
  workspaceId: string;
  runId: string;
  s: State;
  setS: React.Dispatch<React.SetStateAction<State>>;
  router: ReturnType<typeof useRouter>;
}

function useAutoResume({ workspaceId, runId, s, setS, router }: AutoResumeArgs): void {
  useEffect(() => {
    if (!shouldAutoResume(s)) return;
    let cancelled = false;
    setS((p) => ({ ...p, resuming: true }));
    void runAutoResume(workspaceId, runId, () => cancelled, router, () =>
      setS((p) => ({ ...p, resuming: false })),
    );
    return () => { cancelled = true; };
  }, [workspaceId, runId, s, setS, router]);
}

function shouldAutoResume(s: State): boolean {
  if (!s.run || !s.reviews || s.resuming) return false;
  if (s.run.status !== "needs_review") return false;
  if (s.reviews.length === 0) return false;
  return s.reviews.every((r) => r.status !== "pending");
}

async function runAutoResume(
  workspaceId: string,
  runId: string,
  isCancelled: () => boolean,
  router: ReturnType<typeof useRouter>,
  onError: () => void,
): Promise<void> {
  try {
    await resumePipelineRun(workspaceId, runId);
    if (isCancelled()) return;
    toast.success("Revisões concluídas. Pipeline retomado.", { duration: 4000 });
    router.push("/pipeline");
  } catch (err) {
    if (isCancelled()) return;
    toast.error(err instanceof ApiError ? err.detail : "Erro ao retomar pipeline");
    onError();
  }
}
