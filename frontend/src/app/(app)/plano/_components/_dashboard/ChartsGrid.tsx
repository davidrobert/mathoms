"use client";

import type { DashboardChart } from "@/lib/api";
import { BarChartCard } from "./BarChartCard";
import { ChartSkeleton } from "./ChartSkeleton";
import { PieChartCard } from "./PieChartCard";

function isDespesasCategoryChart(title: string): boolean {
  const t = title.toLowerCase();
  return t.includes("categoria") || t.includes("despesas por");
}

function ChartCard({
  chart,
  onBarClick,
  onSliceClick,
}: {
  chart: DashboardChart;
  onBarClick: (label: string) => void;
  onSliceClick: (name: string) => void;
}) {
  if (chart.chart_type === "pie") {
    const pieHandler = isDespesasCategoryChart(chart.title) ? onSliceClick : undefined;
    return <PieChartCard chart={chart} onSliceClick={pieHandler} />;
  }
  return <BarChartCard chart={chart} onBarClick={onBarClick} />;
}

export function ChartsGrid({
  loading,
  charts,
  onBarClick,
  onSliceClick,
}: {
  loading: boolean;
  charts: DashboardChart[];
  onBarClick: (label: string) => void;
  onSliceClick: (name: string) => void;
}) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <ChartSkeleton key={i} />
        ))}
      </div>
    );
  }
  if (charts.length === 0) return null;
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      {charts.map((chart) => (
        <ChartCard
          key={chart.title}
          chart={chart}
          onBarClick={onBarClick}
          onSliceClick={onSliceClick}
        />
      ))}
    </div>
  );
}
