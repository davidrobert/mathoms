"use client";

import type { DashboardAlert } from "@/lib/api";

import {
  alertTone,
  summarizeUrgentPoints,
  urgentPointsLabel,
} from "./alertTone";

/** Sinal do summary fechado da "Análise Financeira". Antes dos dados não renderiza nada —
 * nem "0", nem skeleton —, e a altura cabe na linha do texto: o summary não pisca, e só
 * a régua à direita encolhe quando o chip chega. */
export function UrgentPointsChip({
  alerts,
}: {
  alerts: readonly DashboardAlert[] | null;
}) {
  const summary = summarizeUrgentPoints(alerts ?? []);
  if (summary.total === 0) return null;
  const tone = alertTone(summary.highPriority > 0 ? "critical" : "warning");
  const Icon = tone.icon;
  return (
    <span
      data-testid="urgent-points-chip"
      data-tone={tone.name}
      className={`inline-flex min-h-4 shrink-0 items-center gap-1 whitespace-nowrap rounded-full px-2 text-[0.65rem] normal-case leading-4 tracking-normal ${tone.chipClassName}`}
    >
      <Icon className="h-3 w-3 shrink-0" aria-hidden="true" />
      {urgentPointsLabel(summary)}
    </span>
  );
}
