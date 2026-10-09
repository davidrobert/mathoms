"use client";

import type { DashboardResponse } from "@/lib/api";

import { ChevronOpenIcon } from "../ChevronOpenIcon";
import { AlertCard } from "./AlertCard";
import { ChartsGrid } from "./ChartsGrid";
import { KpiRow as DashboardKpiRow } from "./KpiRow";
import { UrgentPointsChip } from "./UrgentPointsChip";

interface FinancialAnalysisDetailsProps {
  loading: boolean;
  data: DashboardResponse | null;
  onBarClick: (label: string) => void;
  onSliceClick: (name: string) => void;
}

/** Onda 7 #1 — "Análise Financeira" colapsada por default, para reduzir scroll
 * na leitura mensal típica (estratégia → ação primeiro; análise como footer).
 * Fechada, ela ainda sinaliza: o summary conta os pontos urgentes da última
 * análise (`UrgentPointsChip`). O título não declara base temporal: as bases
 * são mistas (janela de até 12 meses documentados, fotografia da posição) e a
 * base pertence ao rótulo de cada item (ADR-306 D1). */
export function FinancialAnalysisDetails({
  loading,
  data,
  onBarClick,
  onSliceClick,
}: FinancialAnalysisDetailsProps) {
  return (
    <details className="group my-8">
      <summary className="flex cursor-pointer list-none flex-wrap items-center gap-x-3 gap-y-1 py-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground hover:text-foreground">
        <ChevronOpenIcon />
        Análise Financeira
        <span className="hidden text-[10px] font-normal normal-case tracking-normal opacity-70 sm:inline">
          (alertas, indicadores e gráficos da última análise — abra para ver)
        </span>
        <UrgentPointsChip alerts={data?.alerts ?? null} />
        <span className="flex-1 border-t border-border" />
      </summary>
      <div className="mt-6">
        {data && data.alerts.length > 0 && (
          <div className="mb-6 space-y-3">
            {data.alerts.map((alert, i) => (
              <AlertCard key={`${alert.kind}-${i}`} alert={alert} />
            ))}
          </div>
        )}
        <DashboardKpiRow loading={loading} kpis={data?.kpis ?? []} />
        <ChartsGrid
          loading={loading}
          charts={data?.charts ?? []}
          onBarClick={onBarClick}
          onSliceClick={onSliceClick}
        />
      </div>
    </details>
  );
}
