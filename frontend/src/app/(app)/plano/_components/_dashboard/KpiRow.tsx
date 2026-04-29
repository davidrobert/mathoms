"use client";

import { ArrowUpDown, PiggyBank, TrendingUp, Wallet } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { DashboardKPI } from "@/lib/api";
import { KPICard } from "@/components/KPICard";

const KPI_ICONS: LucideIcon[] = [TrendingUp, Wallet, PiggyBank, ArrowUpDown];

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
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <KPICard key={i} label="" value="" loading />
        ))}
      </div>
    );
  }
  return (
    <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {kpis.map((kpi, i) => (
        <KPICard
          key={kpi.label}
          label={kpi.label}
          value={kpi.value}
          icon={KPI_ICONS[i % KPI_ICONS.length]}
          emphasis={i === 0 ? "primary" : "secondary"}
          delta={kpiDeltaProps(kpi)}
        />
      ))}
    </div>
  );
}
