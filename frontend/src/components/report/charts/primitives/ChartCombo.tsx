"use client";

import { useMemo } from "react";
import type { ChartData, ChartOptions } from "chart.js";
import { ChartCanvas } from "./ChartCanvas";
import { useChartTheme } from "./useChartTheme";
import type { ChartBaseProps, ChartSeries } from "./types";

export interface ChartComboSeries extends ChartSeries {
  readonly kind: "bar" | "line";
  readonly yAxisID?: "y" | "y1";
}

export interface ChartComboProps extends ChartBaseProps {
  readonly labels: readonly string[];
  readonly series: readonly ChartComboSeries[];
  readonly dualAxis?: boolean;
  readonly formatValue?: (v: number) => string;
}

const BRL = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 0,
});

export function ChartCombo({
  labels,
  series,
  dualAxis = false,
  formatValue = (v) => BRL.format(v),
  height = "auto",
  ariaLabel,
  ...rest
}: ChartComboProps) {
  const theme = useChartTheme();

  const data = useMemo<ChartData>(
    () => ({
      labels: [...labels],
      datasets: series.map((s, i) => {
        const color = s.color ?? theme.categorical[i % theme.categorical.length];
        const yAxisID = s.yAxisID ?? "y";
        if (s.kind === "line") {
          return {
            type: "line" as const,
            label: s.label,
            data: [...s.data],
            borderColor: color,
            backgroundColor: color,
            borderWidth: 2,
            tension: 0.35,
            pointRadius: 3,
            yAxisID,
          };
        }
        return {
          type: "bar" as const,
          label: s.label,
          data: [...s.data],
          backgroundColor: color,
          borderRadius: 4,
          yAxisID,
        };
      }),
    }),
    [labels, series, theme.categorical],
  );

  const options = useMemo<ChartOptions>(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "top", labels: { color: theme.text } },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.dataset.label}: ${formatValue(Number(ctx.parsed.y))}`,
          },
        },
      },
      scales: {
        x: {
          grid: { color: theme.grid, display: false },
          ticks: { color: theme.textMuted },
        },
        y: {
          position: "left",
          grid: { color: theme.grid },
          ticks: { color: theme.textMuted, callback: (v) => formatValue(Number(v)) },
        },
        ...(dualAxis
          ? {
              y1: {
                position: "right" as const,
                grid: { display: false },
                ticks: {
                  color: theme.textMuted,
                  callback: (v: number | string) => formatValue(Number(v)),
                },
              },
            }
          : {}),
      },
    }),
    [dualAxis, theme, formatValue],
  );

  return (
    <ChartCanvas
      type="bar"
      data={data as ChartData<"bar">}
      options={options as ChartOptions<"bar">}
      height={height}
      ariaLabel={ariaLabel ?? rest.title}
      data-testid={rest["data-testid"]}
    />
  );
}
