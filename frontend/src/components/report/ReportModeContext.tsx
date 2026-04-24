"use client";

import { createContext, useContext } from "react";
import type { ReportMode } from "@/generated/report-layout";

export const VALID_MODES = new Set<ReportMode>(["estrategico", "tatico", "usa"]);

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
