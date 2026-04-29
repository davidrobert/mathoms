"use client";

/**
 * Direção E · Onda 7 #5 — sinais de "workspace zero" para `/plano`.
 *
 * Detecta o estado em que ainda não há nada para o casal olhar:
 * sem meta IF, sem decisões, sem tarefas. Quando vazio, `/plano`
 * substitui o resto do conteúdo pelo `<OnboardingHero/>`.
 */

import { useEffect, useState } from "react";

import { listDecisions, listTasks } from "@/lib/api";

export interface WorkspaceZeroSignals {
  decisionCount: number;
  taskCount: number;
  loading: boolean;
}

interface ZeroCounts {
  decisions: number;
  tasks: number;
}

export function useWorkspaceZeroSignals(
  workspaceId: string | undefined,
): WorkspaceZeroSignals {
  const [counts, setCounts] = useState<ZeroCounts>({ decisions: 0, tasks: 0 });
  const [loading, setLoading] = useState(true);
  useEffect(() => runZeroLoadEffect(workspaceId, setCounts, setLoading), [workspaceId]);
  return {
    decisionCount: counts.decisions,
    taskCount: counts.tasks,
    loading,
  };
}

function runZeroLoadEffect(
  workspaceId: string | undefined,
  setCounts: (c: ZeroCounts) => void,
  setLoading: (b: boolean) => void,
): () => void {
  if (!workspaceId) {
    setLoading(false);
    return () => {};
  }
  let cancelled = false;
  void loadZeroCounts(workspaceId).then((next) => {
    if (cancelled) return;
    setCounts(next);
    setLoading(false);
  });
  return () => {
    cancelled = true;
  };
}

async function loadZeroCounts(workspaceId: string): Promise<ZeroCounts> {
  const [d, t] = await Promise.allSettled([
    listDecisions(workspaceId),
    listTasks(workspaceId, {
      include_done: false,
      include_cancelled: false,
    }),
  ]);
  return {
    decisions: d.status === "fulfilled" ? d.value.total : 0,
    tasks: t.status === "fulfilled" ? t.value.total : 0,
  };
}
