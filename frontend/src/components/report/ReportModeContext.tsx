"use client";

import { createContext, useContext } from "react";
import type { ReportMode } from "@/generated/report-layout";

// TEMP: modo "usa" oculto da UI — `?mode=usa` na URL agora cai no default.
// Para restaurar, adicionar "usa" de volta ao set.
export const VALID_MODES = new Set<ReportMode>(["estrategico", "tatico"]);

export interface ReportModeContextValue {
  mode: ReportMode;
  setMode: (mode: ReportMode) => void;
}

export const ReportModeContext = createContext<ReportModeContextValue | null>(
  null,
);

export function useReportMode(): ReportModeContextValue {
  const ctx = useContext(ReportModeContext);
  if (!ctx) {
    throw new Error(
      "useReportMode deve ser usado dentro de <ReportModeProvider>",
    );
  }
  return ctx;
}
