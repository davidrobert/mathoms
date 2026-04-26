import { useMemo } from "react";

import type { Period } from "@/components/report/ui/PeriodToggle";

export interface PeriodWindow {
  readonly start: number;
  readonly end: number;
  readonly label: string;
}

const PT_BR_MONTHS: Record<string, number> = {
  jan: 1,
  fev: 2,
  mar: 3,
  abr: 4,
  mai: 5,
  jun: 6,
  jul: 7,
  ago: 8,
  set: 9,
  out: 10,
  nov: 11,
  dez: 12,
};

interface ParsedLabel {
  readonly year: number;
  readonly month: number;
}

const TRAILING_MONTHS: Record<Exclude<Period, "ytd">, number> = {
  "3m": 3,
  "6m": 6,
  "12m": 12,
};

/** Aceita "YY/MM" (numérico, ex.: "26/02") ou "mes/aa" pt-BR (ex.: "fev/26").
 * Backend hoje gera o formato numérico (`fluxo_caixa_enricher.py:284`); o
 * formato pt-BR é suportado para fixtures e outros consumidores. */
function parseLabel(label: string): ParsedLabel | null {
  const trimmed = label.trim().toLowerCase();
  const numeric = /^(\d{2})\/(\d{2})$/.exec(trimmed);
  if (numeric) {
    const yy = Number(numeric[1]);
    const mm = Number(numeric[2]);
    if (mm >= 1 && mm <= 12) return { year: 2000 + yy, month: mm };
    return null;
  }
  const named = /^([a-zç]{3})\/(\d{2})$/.exec(trimmed);
  if (named) {
    const month = PT_BR_MONTHS[named[1]];
    if (!month) return null;
    return { year: 2000 + Number(named[2]), month };
  }
  return null;
}

function formatRangeLabel(allLabels: readonly string[], start: number, end: number): string {
  if (end <= start) return "";
  const first = allLabels[start];
  const last = allLabels[end - 1];
  if (!first || !last) return "";
  if (first === last) return first;
  return `${first} — ${last}`;
}

function ytdWindow(
  allLabels: readonly string[],
  anchorDate: Date | undefined,
): { start: number; end: number } {
  const len = allLabels.length;
  if (len === 0) return { start: 0, end: 0 };
  const lastParsed = parseLabel(allLabels[len - 1]);
  const referenceYear = anchorDate
    ? anchorDate.getFullYear()
    : (lastParsed?.year ?? new Date().getFullYear());
  const firstIdx = allLabels.findIndex((lbl) => {
    const parsed = parseLabel(lbl);
    return parsed?.year === referenceYear && parsed?.month === 1;
  });
  if (firstIdx === -1) {
    const fallback = allLabels.findIndex((lbl) => parseLabel(lbl)?.year === referenceYear);
    if (fallback === -1) return { start: Math.max(0, len - 12), end: len };
    return { start: fallback, end: len };
  }
  return { start: firstIdx, end: len };
}

function computeRange(
  allLabels: readonly string[],
  period: Period,
  anchorDate: Date | undefined,
): { start: number; end: number } {
  const len = allLabels.length;
  if (period === "ytd") return ytdWindow(allLabels, anchorDate);
  const trailing = TRAILING_MONTHS[period];
  return { start: Math.max(0, len - trailing), end: len };
}

/** v2.E.1 — Calcula a janela [start, end) e o label "first — last" para um
 * dado conjunto de labels mensais e um {@link Period} escolhido.
 *
 * Hook puro: zero side-effects, memo só para estabilizar referência. Usado
 * por charts que escutam `<PeriodToggle>` (E.3/E.4/E.5).
 *
 * @param allLabels labels do eixo X (ex.: `["26/01", "26/02", ...]`).
 * @param period janela escolhida pelo usuário.
 * @param anchorDate âncora para o cálculo de YTD (default: ano do último label).
 */
export function usePeriodWindow(
  allLabels: readonly string[],
  period: Period,
  anchorDate?: Date,
): PeriodWindow {
  return useMemo(() => {
    if (allLabels.length === 0) return { start: 0, end: 0, label: "" };
    const { start, end } = computeRange(allLabels, period, anchorDate);
    return { start, end, label: formatRangeLabel(allLabels, start, end) };
  }, [allLabels, period, anchorDate]);
}
