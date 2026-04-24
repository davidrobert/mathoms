"use client";

import { useEffect, useMemo, useState } from "react";

/** ADR-117 · Fase 2 — resolve cores dos charts a partir dos tokens CSS.
 *
 * Lê CSS vars do `:root` + `[data-theme='dark']` em runtime e retorna
 * paleta tipada para os primitivos de chart. Re-calcula quando
 * `data-theme` muda no `<html>` (via MutationObserver).
 *
 * Fora do browser (SSR) retorna valores light como fallback — os charts
 * são `ssr: false` então esse caminho quase nunca executa.
 */
export interface ChartPalette {
  readonly text: string;
  readonly textMuted: string;
  readonly grid: string;
  readonly border: string;
  readonly surface: string;
  readonly primary: string;
  readonly accent: string;
  readonly danger: string;
  readonly warning: string;
  readonly info: string;
  readonly categorical: readonly string[];
}

const LIGHT_FALLBACK: ChartPalette = {
  text: "#0F172A",
  textMuted: "#64748B",
  grid: "#E2E8F0",
  border: "#E2E8F0",
  surface: "#FFFFFF",
  primary: "#1A3A5C",
  accent: "#15803D",
  danger: "#B91C1C",
  warning: "#F4A261",
  info: "#1E6E8F",
  categorical: [
    "#1A3A5C", "#15803D", "#B91C1C", "#F4A261",
    "#6D28D9", "#0891B2", "#CA8A04", "#BE185D",
    "#166534", "#9F1239", "#0369A1", "#A16207",
  ],
};

function readVar(root: HTMLElement, name: string, fallback: string): string {
  const value = getComputedStyle(root).getPropertyValue(name).trim();
  return value || fallback;
}

function resolvePalette(): ChartPalette {
  if (typeof document === "undefined") return LIGHT_FALLBACK;
  const root = document.documentElement;
  const categorical: string[] = [];
  for (let i = 1; i <= 12; i++) {
    const c = readVar(root, `--chart-${i}`, LIGHT_FALLBACK.categorical[i - 1]);
    categorical.push(c);
  }
  return {
    text: readVar(root, "--surface-foreground", LIGHT_FALLBACK.text),
    textMuted: readVar(root, "--surface-muted-foreground", LIGHT_FALLBACK.textMuted),
    grid: readVar(root, "--surface-border", LIGHT_FALLBACK.grid),
    border: readVar(root, "--surface-border", LIGHT_FALLBACK.border),
    surface: readVar(root, "--surface-card", LIGHT_FALLBACK.surface),
    primary: readVar(root, "--brand-primary", LIGHT_FALLBACK.primary),
    accent: readVar(root, "--brand-accent", LIGHT_FALLBACK.accent),
    danger: readVar(root, "--brand-danger", LIGHT_FALLBACK.danger),
    warning: readVar(root, "--brand-warning", LIGHT_FALLBACK.warning),
    info: readVar(root, "--brand-info", LIGHT_FALLBACK.info),
    categorical,
  };
}

export function useChartTheme(): ChartPalette {
  const [palette, setPalette] = useState<ChartPalette>(LIGHT_FALLBACK);

  useEffect(() => {
    setPalette(resolvePalette());
    const root = document.documentElement;
    const observer = new MutationObserver(() => {
      setPalette(resolvePalette());
    });
    observer.observe(root, { attributes: true, attributeFilter: ["class", "data-theme"] });
    return () => observer.disconnect();
  }, []);

  return useMemo(() => palette, [palette]);
}
