"use client";

import { useEffect, useState } from "react";

import {
  computeIFGoal,
  getAlocacaoGoal,
  getAporteGoal,
  getDolarGoal,
  getIFGoal,
  listReports,
  listTasksForGoal,
  type AlocacaoGoalResponse,
  type AporteGoalResponse,
  type DolarGoalResponse,
  type IFGoalResponse,
  type TaskResponse,
} from "@/lib/api";

export interface PlanoGoals {
  ifGoal: IFGoalResponse | null;
  aporteGoal: AporteGoalResponse | null;
  dolarGoal: DolarGoalResponse | null;
  alocacaoGoal: AlocacaoGoalResponse | null;
}

export interface IFProgress {
  pct: number;
  faltante: number;
}

/** Direção E · Onda 7 #4 (ADR-156) — fonte única de patrimônio em /plano.
 *
 * Toda exibição de patrimônio em /plano (KPI row + Hero IF) consome
 * `patrimonio_snapshot.value` deste hook. Não recompute em outro lugar
 * nem peça `progress.patrimonio` — o campo foi removido do `IFProgress`.
 */
export interface PatrimonioSnapshot {
  value: number;
  asOf: string;
  sourceReportId: string;
}

interface UsePlanoOverviewResult {
  goals: PlanoGoals;
  linkedTasks: TaskResponse[];
  progress: IFProgress | null;
  patrimonio_snapshot: PatrimonioSnapshot | null;
  loading: boolean;
  error: string | null;
}

interface PlanoSetters {
  setGoals: (g: PlanoGoals) => void;
  setLinkedTasks: (t: TaskResponse[]) => void;
  setProgress: (p: IFProgress | null) => void;
  setSnapshot: (s: PatrimonioSnapshot | null) => void;
  setLoading: (b: boolean) => void;
  setError: (s: string | null) => void;
}

const EMPTY_GOALS: PlanoGoals = {
  ifGoal: null,
  aporteGoal: null,
  dolarGoal: null,
  alocacaoGoal: null,
};

export function usePlanoOverview(
  workspaceId: string | undefined
): UsePlanoOverviewResult {
  const [goals, setGoals] = useState<PlanoGoals>(EMPTY_GOALS);
  const [linkedTasks, setLinkedTasks] = useState<TaskResponse[]>([]);
  const [progress, setProgress] = useState<IFProgress | null>(null);
  const [snapshot, setSnapshot] = useState<PatrimonioSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!workspaceId) return;
    let cancelled = false;
    const setters: PlanoSetters = {
      setGoals,
      setLinkedTasks,
      setProgress,
      setSnapshot,
      setLoading,
      setError,
    };
    runPlanoLoad(workspaceId, setters, () => cancelled);
    return () => {
      cancelled = true;
    };
  }, [workspaceId]);

  return {
    goals,
    linkedTasks,
    progress,
    patrimonio_snapshot: snapshot,
    loading,
    error,
  };
}

async function runPlanoLoad(
  wsId: string,
  setters: PlanoSetters,
  isCancelled: () => boolean
) {
  setters.setLoading(true);
  setters.setError(null);
  try {
    const loadedGoals = await loadAllGoals(wsId);
    if (isCancelled()) return;
    setters.setGoals(loadedGoals);

    const snapshot = await loadLatestPatrimonioSnapshot(wsId);
    if (isCancelled()) return;
    setters.setSnapshot(snapshot);

    if (loadedGoals.ifGoal && snapshot != null) {
      const [tasks, ifProgress] = await loadIFExtras(
        wsId,
        loadedGoals.ifGoal,
        snapshot.value
      );
      if (isCancelled()) return;
      setters.setLinkedTasks(tasks);
      setters.setProgress(ifProgress);
    }
  } catch (err: unknown) {
    if (!isCancelled()) setters.setError(errorMessage(err));
  } finally {
    if (!isCancelled()) setters.setLoading(false);
  }
}

async function loadLatestPatrimonioSnapshot(
  wsId: string
): Promise<PatrimonioSnapshot | null> {
  try {
    const { reports } = await listReports(wsId);
    const latest = reports.find((r) => r.patrimonio_liquido != null);
    if (!latest || latest.patrimonio_liquido == null) return null;
    return {
      value: latest.patrimonio_liquido,
      asOf: latest.created_at,
      sourceReportId: latest.id,
    };
  } catch {
    return null;
  }
}

function errorMessage(err: unknown): string {
  return err instanceof Error
    ? err.message
    : "Erro ao carregar o plano. Tente novamente.";
}

async function loadAllGoals(wsId: string): Promise<PlanoGoals> {
  const [ifResult, aporteResult, dolarResult, alocacaoResult] =
    await Promise.allSettled([
      getIFGoal(wsId),
      getAporteGoal(wsId),
      getDolarGoal(wsId),
      getAlocacaoGoal(wsId),
    ]);

  return {
    ifGoal: ifResult.status === "fulfilled" ? ifResult.value : null,
    aporteGoal:
      aporteResult.status === "fulfilled" ? aporteResult.value : null,
    dolarGoal: dolarResult.status === "fulfilled" ? dolarResult.value : null,
    alocacaoGoal:
      alocacaoResult.status === "fulfilled" ? alocacaoResult.value : null,
  };
}

async function loadIFExtras(
  wsId: string,
  ifGoal: IFGoalResponse,
  patrimonio: number
): Promise<[TaskResponse[], IFProgress | null]> {
  const [tasksResult, progressResult] = await Promise.allSettled([
    listTasksForGoal(wsId, ifGoal.id, false),
    computeIFProgress(wsId, ifGoal, patrimonio),
  ]);
  const tasks =
    tasksResult.status === "fulfilled" ? tasksResult.value.tasks : [];
  const ifProgress =
    progressResult.status === "fulfilled" ? progressResult.value : null;
  return [tasks, ifProgress];
}

async function computeIFProgress(
  wsId: string,
  goalData: IFGoalResponse,
  patrimonio: number
): Promise<IFProgress | null> {
  const result = await computeIFGoal(wsId, {
    inputs: goalData.inputs,
    patrimonio_atual_brl: patrimonio,
  });
  if (result.percentual_conquistado == null || result.faltante_brl == null) {
    return null;
  }
  return {
    pct: result.percentual_conquistado,
    faltante: result.faltante_brl,
  };
}
