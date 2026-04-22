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
  patrimonio: number;
}

interface UsePlanoOverviewResult {
  goals: PlanoGoals;
  linkedTasks: TaskResponse[];
  progress: IFProgress | null;
  loading: boolean;
  error: string | null;
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!workspaceId) return;
    let cancelled = false;

    async function load(wsId: string) {
      setLoading(true);
      setError(null);
      try {
        const loadedGoals = await loadAllGoals(wsId);
        if (cancelled) return;
        setGoals(loadedGoals);

        if (loadedGoals.ifGoal) {
          const [tasks, ifProgress] = await loadIFExtras(
            wsId,
            loadedGoals.ifGoal
          );
          if (cancelled) return;
          setLinkedTasks(tasks);
          setProgress(ifProgress);
        }
      } catch (err: unknown) {
        if (cancelled) return;
        setError(
          err instanceof Error
            ? err.message
            : "Erro ao carregar o plano. Tente novamente."
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load(workspaceId);
    return () => {
      cancelled = true;
    };
  }, [workspaceId]);

  return { goals, linkedTasks, progress, loading, error };
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
  ifGoal: IFGoalResponse
): Promise<[TaskResponse[], IFProgress | null]> {
  const [tasksResult, progressResult] = await Promise.allSettled([
    listTasksForGoal(wsId, ifGoal.id, false),
    loadIFProgress(wsId, ifGoal),
  ]);
  const tasks =
    tasksResult.status === "fulfilled" ? tasksResult.value.tasks : [];
  const ifProgress =
    progressResult.status === "fulfilled" ? progressResult.value : null;
  return [tasks, ifProgress];
}

async function loadIFProgress(
  wsId: string,
  goalData: IFGoalResponse
): Promise<IFProgress | null> {
  try {
    const { reports } = await listReports(wsId);
    const latest = reports.find((r) => r.patrimonio_liquido != null);
    if (!latest?.patrimonio_liquido) return null;

    const result = await computeIFGoal(wsId, {
      inputs: goalData.inputs,
      patrimonio_atual_brl: latest.patrimonio_liquido,
    });

    if (
      result.percentual_conquistado != null &&
      result.faltante_brl != null
    ) {
      return {
        pct: result.percentual_conquistado,
        faltante: result.faltante_brl,
        patrimonio: latest.patrimonio_liquido,
      };
    }
  } catch {
    // Progresso is nice-to-have
  }
  return null;
}
