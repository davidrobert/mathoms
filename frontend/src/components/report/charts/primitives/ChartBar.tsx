"use client";

import { useMemo } from "react";
import type { ChartData, ChartOptions } from "chart.js";
import { ChartCanvas } from "./ChartCanvas";
import { useChartTheme } from "./useChartTheme";
import type { ChartBaseProps, ChartSeries } from "./types";

export interface ChartBarProps extends ChartBaseProps {
  readonly labels: readonly string[];
  readonly series: readonly ChartSeries[];
  readonly stacked?: boolean;
  readonly horizontal?: boolean;
  readonly formatValue?: (v: number) => string;
}

const DEFAULT_FORMATTER = (v: number): string =>
  new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(v);

export function ChartBar({
  labels,
  series,
  stacked = false,
  horizontal = false,
  formatValue = DEFAULT_FORMATTER,
  height = "auto",
  ariaLabel,
  ...rest
}: ChartBarProps) {
  const theme = useChartTheme();

  const data = useMemo<ChartData<"bar">>(
    () => ({
      labels: [...labels],
      datasets: series.map((s, i) => ({
        label: s.label,
        data: [...s.data],
        backgroundColor: s.color ?? theme.categorical[i % theme.categorical.length],
        borderRadius: 4,
        borderSkipped: false,
      })),
    }),
    [labels, series, theme.categorical],
  );

  const options = useMemo<ChartOptions<"bar">>(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: horizontal ? "y" : "x",
      plugins: {
        legend: {
          display: series.length > 1,
          position: "top",
          labels: { color: theme.text },
        },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const v = ctx.parsed[horizontal ? "x" : "y"];
              return `${ctx.dataset.label}: ${formatValue(v ?? 0)}`;
            },
          },
        },
      },
      scales: {
        x: {
          stacked,
          grid: { color: theme.grid, display: !horizontal },
          ticks: { color: theme.textMuted },
        },
        y: {
          stacked,
          grid: { color: theme.grid, display: horizontal },
          ticks: {
            color: theme.textMuted,
            callback: (v) => (horizontal ? v : formatValue(Number(v))),
          },
        },
      },
    }),
    [stacked, horizontal, series.length, theme, formatValue],
  );

  return (
    <ChartCanvas
      type="bar"
      data={data}
      options={options}
      height={height}
      ariaLabel={ariaLabel ?? rest.title}
      data-testid={rest["data-testid"]}
    />
  );
}

/** Stacked bar — atalho para ChartBar com stacked=true. */
export function ChartStackedBar(props: Omit<ChartBarProps, "stacked">) {
  return <ChartBar {...props} stacked />;
}
