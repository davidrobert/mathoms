"use client";

import { useEffect, useState, useCallback } from "react";

/** ADR-121 — typography configurável no escopo de `/reports/**`.
 *
 * Três presets (base px: 14/16/18) aplicados via `data-font-scale` no
 * wrapper `[data-report-scope]`. Persiste em localStorage. Default `normal`
 * (16px) — refinement 2026-04-26: 13px era mesquinho para tabela monetária.
 *
 * Este hook não injeta UI — só expõe `(scale, setScale)`. UI vive em
 * `AppearanceMenu` (popover Aa unificado fonte+tema).
 */
export type ReportFontScale = "compact" | "normal" | "comfortable";

const STORAGE_KEY = "mathoms:report:font-scale";
const DEFAULT_SCALE: ReportFontScale = "normal";
const VALID_SCALES: ReportFontScale[] = ["compact", "normal", "comfortable"];

function readStoredScale(): ReportFontScale {
  if (typeof window === "undefined") return DEFAULT_SCALE;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw && VALID_SCALES.includes(raw as ReportFontScale)) {
      return raw as ReportFontScale;
    }
  } catch {
    // SecurityError em iframes com storage bloqueado — ignora silenciosamente
  }
  return DEFAULT_SCALE;
}

export function useReportFontScale(): {
  scale: ReportFontScale;
  setScale: (s: ReportFontScale) => void;
} {
  const [scale, setScaleState] = useState<ReportFontScale>(DEFAULT_SCALE);

  useEffect(() => {
    setScaleState(readStoredScale());
  }, []);

  const setScale = useCallback((next: ReportFontScale) => {
    setScaleState(next);
    if (typeof window !== "undefined") {
      try {
        window.localStorage.setItem(STORAGE_KEY, next);
      } catch {
        // ignore
      }
    }
  }, []);

  return { scale, setScale };
}
