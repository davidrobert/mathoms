"use client";

import { useMemo } from "react";
import type { ChartData, ChartOptions } from "chart.js";
import { ChartCanvas } from "./ChartCanvas";
import { useChartTheme } from "./useChartTheme";
import type { ChartBaseProps } from "./types";

export interface WaterfallStep {
  readonly label: string;
  readonly value: number;
  /** "start"/"end" renderizam barra sólida a partir de zero; "delta" usa floating bar. */
  readonly kind?: "start" | "delta" | "end";
}

export interface ChartWaterfallProps extends ChartBaseProps {
  readonly steps: readonly WaterfallStep[];
  readonly formatValue?: (v: number) => string;
  /** v2.E.9 — formatter dos ticks do eixo Y (default: `formatValue`).
   *  Permite eixo compacto ("1,5 mi") mantendo tooltip por extenso. */
  readonly formatAxisValue?: (v: number) => string;
}

const BRL = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 0,
});

/**
 * Waterfall via Chart.js bar com floating bars. Cada barra recebe par
 * [base, top] — positivos em verde, negativos em vermelho, pilares
 * (start/end) em azul primary.
 */
export function ChartWaterfall({
  steps,
  formatValue = (v) => BRL.format(v),
  formatAxisValue = formatValue,
  height = "auto",
  ariaLabel,
  ...rest
}: ChartWaterfallProps) {
  const theme = useChartTheme();

  const { floatData, colors } = useMemo(() => {
    const fdata: [number, number][] = [];
    const cs: string[] = [];
    let running = 0;
    steps.forEach((step, i) => {
      const kind = step.kind ?? (i === 0 ? "start" : i === steps.length - 1 ? "end" : "delta");
      if (kind === "start" || kind === "end") {
        fdata.push([0, step.value]);
        cs.push(theme.primary);
        running = step.value;
      } else {
        const base = running;
        const top = running + step.value;
        fdata.push([Math.min(base, top), Math.max(base, top)]);
        cs.push(step.value >= 0 ? theme.accent : theme.danger);
        running = top;
      }
    });
    return { floatData: fdata, colors: cs };
  }, [steps, theme.accent, theme.danger, theme.primary]);

  const data = useMemo<ChartData<"bar">>(
    () => ({
      labels: steps.map((s) => s.label),
      datasets: [
        {
          label: "",
          data: floatData as unknown as number[], // Chart.js aceita [a,b] em bar
          backgroundColor: colors,
          borderRadius: 4,
          borderSkipped: false,
        },
      ],
    }),
    [steps, floatData, colors],
  );

  const options = useMemo<ChartOptions<"bar">>(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const step = steps[ctx.dataIndex];
              return `${step.label}: ${formatValue(step.value)}`;
            },
          },
        },
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: theme.textMuted } },
        y: {
          grid: { color: theme.grid },
          ticks: { color: theme.textMuted, callback: (v) => formatAxisValue(Number(v)) },
        },
      },
    }),
    [steps, theme, formatValue, formatAxisValue],
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
