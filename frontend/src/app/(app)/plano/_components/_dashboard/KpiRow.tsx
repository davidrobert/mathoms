"use client";

import { PiggyBank, TrendingUp } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { DashboardKPI } from "@/lib/api";
import { KPICard } from "@/components/KPICard";

/** Ícone pelo KPI, não pela posição: o backend omite o KPI sem dado, e a posição
 *  deslizaria o ícone para o vizinho. */
const KPI_ICONS: Record<string, LucideIcon> = {
  taxa_de_poupanca: PiggyBank,
  score_financeiro: TrendingUp,
};

/** Os KPIs que `build_kpis` emite; o skeleton desenha o mesmo número para não saltar. */
const KPI_SLOTS = 2;

function kpiDeltaProps(kpi: DashboardKPI) {
  if (kpi.delta == null) return undefined;
  return {
    value: kpi.delta,
    percent: kpi.delta_percent ?? undefined,
  };
}

export function KpiRow({
  loading,
  kpis,
}: {
  loading: boolean;
  kpis: DashboardKPI[];
}) {
  if (loading) {
    return (
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
        {Array.from({ length: KPI_SLOTS }).map((_, i) => (
          <KPICard key={i} label="" value="" loading />
        ))}
      </div>
    );
  }
  return (
    <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
      {kpis.map((kpi, i) => (
        <KPICard
          key={kpi.key}
          label={kpi.label}
          value={kpi.value}
          icon={KPI_ICONS[kpi.key]}
          emphasis={i === 0 ? "primary" : "secondary"}
          delta={kpiDeltaProps(kpi)}
        />
      ))}
    </div>
  );
}
