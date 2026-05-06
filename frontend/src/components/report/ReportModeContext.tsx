"use client";

import { createContext, useContext } from "react";
import type { ReportMode } from "@/generated/report-layout";

// ADR-168 (A8.4 PR4): Modo USA removido. ReportMode é literal único.
export const VALID_MODES = new Set<ReportMode>(["estrategico"]);

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
