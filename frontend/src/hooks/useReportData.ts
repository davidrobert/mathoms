"use client";

import { useEffect, useState } from "react";
import { ApiError, getReportData, type ReportAnalysisData } from "@/lib/api";
export type { ApiError };

export type UseReportDataState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: ReportAnalysisData }
  | { status: "error"; error: ApiError | Error };

/** F9 · ADR-076 — Hook para carregar o snapshot E5 JSON do relatório.
 *
 * Recebe `workspaceId` como parâmetro em vez de chamar `useWorkspace()`
 * internamente — evita dupla chamada de useContext quando o componente pai
 * já tem o workspace como prop (ex: ReportPageContent).
 *
 * `reportId` e `workspaceId` podem ser `null` para desligar o fetch (ex:
 * durante transições de rota). Em caso de 404 de relatório pré-F9 (sem
 * analysis_json_path), o estado fica em `error` com `ApiError.status === 404`.
 */
export function useReportData(
  reportId: string | null,
  workspaceId: string | null,
): UseReportDataState {
  const [state, setState] = useState<UseReportDataState>({ status: "idle" });

  useEffect(() => {
    if (!reportId || !workspaceId) {
      setState({ status: "idle" });
      return;
    }

    let cancelled = false;
    setState({ status: "loading" });

    getReportData(workspaceId, reportId)
      .then((data) => {
        if (!cancelled) setState({ status: "success", data });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        if (error instanceof Error) {
          setState({ status: "error", error });
        } else {
          setState({ status: "error", error: new Error(String(error)) });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [reportId, workspaceId]);

  return state;
}
