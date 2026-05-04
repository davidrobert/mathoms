"use client";

/**
 * Direção E · Onda 10 #6 — sinais de "workspace zero" em /acao.
 *
 * /acao com pending=0, tasks=0 e notes=0 cai no `<EmptyState/>` que
 * redireciona para /plano (entrada canônica). OnboardingHero vive em
 * /plano (Onda 7 #5) — aqui só sinalizamos que /plano é o ponto de
 * partida.
 */

import { useEffect, useState } from "react";

import { listTasks } from "@/lib/api";
import { useWorkspaceNotes } from "@/hooks/useWorkspaceNotes";

import { useSuggestionsCount } from "../../plano/_components/useSuggestionsCount";

export interface AcaoZeroSignals {
  isZero: boolean;
  loading: boolean;
}

export function useAcaoZeroSignals(workspaceId: string | undefined): AcaoZeroSignals {
  const { count: pending, loading: loadingPending } = useSuggestionsCount(workspaceId);
  const { taskCount, loading: loadingTasks } = useTaskCount(workspaceId);
  const { notes, loading: loadingNotes } = useWorkspaceNotes(workspaceId);
  const loading = loadingPending || loadingTasks || loadingNotes;
  const isZero = !loading && pending === 0 && taskCount === 0 && notes.length === 0;
  return { isZero, loading };
}

function useTaskCount(workspaceId: string | undefined) {
  const [taskCount, setTaskCount] = useState(0);
  const [loading, setLoading] = useState(true);
  useEffect(() => runTaskCountEffect(workspaceId, setTaskCount, setLoading), [workspaceId]);
  return { taskCount, loading };
}

async function fetchOpenTaskCount(workspaceId: string): Promise<number> {
  try {
    const res = await listTasks(workspaceId, {
      include_done: false,
      include_cancelled: false,
    });
    return res.total;
  } catch {
    return 0;
  }
}

function runTaskCountEffect(
  workspaceId: string | undefined,
  setTaskCount: (n: number) => void,
  setLoading: (b: boolean) => void,
): () => void {
  if (!workspaceId) {
    setLoading(false);
    return () => {};
  }
  let cancelled = false;
  void fetchOpenTaskCount(workspaceId).then((count) => {
    if (cancelled) return;
    setTaskCount(count);
    setLoading(false);
  });
  return () => {
    cancelled = true;
  };
}
