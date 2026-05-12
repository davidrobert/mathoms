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
  resumeError: string | null;
  canResume: boolean;
  reload: () => Promise<void>;
  resume: () => Promise<void>;
}

interface State {
  reviews: StageReviewResponse[] | null;
  run: PipelineRunResponse | null;
  loading: boolean;
  error: string | null;
  resuming: boolean;
  resumeError: string | null;
}

const INITIAL: State = {
  reviews: null,
  run: null,
  loading: true,
  error: null,
  resuming: false,
  resumeError: null,
};

export function useReviewList(
  workspaceId: string,
  runId: string,
): UseReviewListResult {
  const router = useRouter();
  const [s, setS] = useState<State>(INITIAL);
  const reload = useReloader(workspaceId, runId, setS);
  const resume = useResumer(workspaceId, runId, setS, router);
  useEffect(() => void reload(), [reload]);
  return { ...s, canResume: canResume(s), reload, resume };
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

function useResumer(
  workspaceId: string,
  runId: string,
  setS: React.Dispatch<React.SetStateAction<State>>,
  router: ReturnType<typeof useRouter>,
): () => Promise<void> {
  return useCallback(
    () => runResume(workspaceId, runId, setS, router),
    [workspaceId, runId, setS, router],
  );
}

async function runResume(
  workspaceId: string,
  runId: string,
  setS: React.Dispatch<React.SetStateAction<State>>,
  router: ReturnType<typeof useRouter>,
): Promise<void> {
  setS((p) => ({ ...p, resuming: true, resumeError: null }));
  try {
    await resumePipelineRun(workspaceId, runId);
    toast.success("Pipeline retomado. Acompanhe o progresso abaixo.", {
      duration: 4000,
    });
    router.push("/pipeline");
  } catch (err) {
    const resumeError =
      err instanceof ApiError ? err.detail : "Erro ao retomar pipeline";
    setS((p) => ({ ...p, resuming: false, resumeError }));
  }
}

function canResume(s: State): boolean {
  if (!s.run || !s.reviews) return false;
  if (s.run.status !== "needs_review") return false;
  if (s.reviews.length === 0) return false;
  return s.reviews.every((r) => r.status !== "pending");
}
