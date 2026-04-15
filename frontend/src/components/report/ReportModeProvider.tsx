"use client";

import { createContext, useContext, useState, type ReactNode } from "react";
import type { ReportMode } from "@/generated/report-layout";

interface ReportModeContextValue {
  mode: ReportMode;
  setMode: (mode: ReportMode) => void;
}

const ReportModeContext = createContext<ReportModeContextValue | null>(null);

/** F9 · F1.1 — Provider para o modo ativo do relatório (estrategico/tatico/usa).
 *
 * Substitui o padrão antigo body.mode-* + MutationObserver do iframe —
 * agora o modo é state React, sincronizado com a URL opcionalmente via
 * ?mode= (decisão adiada para F3.2).
 */
export function ReportModeProvider({
  initialMode = "estrategico",
  children,
}: {
  initialMode?: ReportMode;
  children: ReactNode;
}) {
  const [mode, setMode] = useState<ReportMode>(initialMode);
  return (
    <ReportModeContext.Provider value={{ mode, setMode }}>
      {children}
    </ReportModeContext.Provider>
  );
}

export function useReportMode(): ReportModeContextValue {
  const ctx = useContext(ReportModeContext);
  if (!ctx) {
    throw new Error(
      "useReportMode deve ser usado dentro de <ReportModeProvider>",
    );
  }
  return ctx;
}
