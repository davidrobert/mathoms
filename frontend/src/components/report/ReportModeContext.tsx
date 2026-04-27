"use client";

import { createContext, useContext } from "react";
import type { ReportMode } from "@/generated/report-layout";

// TEMP: modo "usa" oculto da UI (toggle/tablist) mas aceito como deep-link
// `?mode=usa` para preservar baselines visuais (v2.2b) e link compartilhável.
// Sections U1-U4 renderizam normalmente quando `mode === "usa"`. UI restaurada
// quando produto retomar — basta adicionar "usa" em `ReportActions.VISIBLE_MODES`.
export const VALID_MODES = new Set<ReportMode>([
  "estrategico",
  "tatico",
  "usa",
]);

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
