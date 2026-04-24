"use client";

import { useMemo } from "react";
import type { ChartData, ChartOptions } from "chart.js";
import { ChartCanvas } from "./ChartCanvas";
import { useChartTheme } from "./useChartTheme";
import type { ChartBaseProps, ChartSeries } from "./types";

export interface ChartLineProps extends ChartBaseProps {
  readonly labels: readonly string[];
  readonly series: readonly ChartSeries[];
  readonly filled?: boolean;
  readonly smooth?: boolean;
  readonly formatValue?: (v: number) => string;
}

const DEFAULT_FORMATTER = (v: number): string =>
  new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(v);

export function ChartLine({
  labels,
  series,
  filled = false,
  smooth = true,
  formatValue = DEFAULT_FORMATTER,
  height = "auto",
  ariaLabel,
  ...rest
}: ChartLineProps) {
  const theme = useChartTheme();

  const data = useMemo<ChartData<"line">>(
    () => ({
      labels: [...labels],
      datasets: series.map((s, i) => {
        const color = s.color ?? theme.categorical[i % theme.categorical.length];
        return {
          label: s.label,
          data: [...s.data],
          borderColor: color,
          backgroundColor: filled ? `${color}33` : color,
          fill: filled,
          tension: smooth ? 0.35 : 0,
          pointRadius: 3,
          pointHoverRadius: 5,
          pointBackgroundColor: color,
        };
      }),
    }),
    [labels, series, theme.categorical, filled, smooth],
  );

  const options = useMemo<ChartOptions<"line">>(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: series.length > 1,
          position: "top",
          labels: { color: theme.text },
        },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.dataset.label}: ${formatValue(ctx.parsed.y ?? 0)}`,
          },
        },
      },
      scales: {
        x: {
          grid: { color: theme.grid, display: false },
          ticks: { color: theme.textMuted },
        },
        y: {
          grid: { color: theme.grid },
          ticks: {
            color: theme.textMuted,
            callback: (v) => formatValue(Number(v)),
          },
        },
      },
    }),
    [series.length, theme, formatValue],
  );

  return (
    <ChartCanvas
      type="line"
      data={data}
      options={options}
      height={height}
      ariaLabel={ariaLabel ?? rest.title}
      data-testid={rest["data-testid"]}
    />
  );
}
