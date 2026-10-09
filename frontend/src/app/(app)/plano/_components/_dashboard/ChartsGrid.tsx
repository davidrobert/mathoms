"use client";

import type { DashboardChart } from "@/lib/api";
import { BarChartCard } from "./BarChartCard";
import { ChartSkeleton } from "./ChartSkeleton";
import { isMonthlyBarChart, isWideChart } from "./dashboardHelpers";
import { PieChartCard } from "./PieChartCard";

function ChartCard({
  chart,
  onBarClick,
  onSliceClick,
}: {
  chart: DashboardChart;
  onBarClick: (label: string) => void;
  onSliceClick: (id: string) => void;
}) {
  if (chart.chart_type === "pie") {
    return <PieChartCard chart={chart} onSliceClick={onSliceClick} />;
  }
  const barHandler = isMonthlyBarChart(chart) ? onBarClick : undefined;
  const span = isWideChart(chart) ? "lg:col-span-2" : undefined;
  return <BarChartCard chart={chart} onBarClick={barHandler} className={span} />;
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
  onSliceClick: (id: string) => void;
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
