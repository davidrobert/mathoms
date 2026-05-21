"use client";

import { useMemo } from "react";
import type { ChartData, ChartOptions } from "chart.js";
import { ChartCanvas } from "./primitives/ChartCanvas";
import { useChartTheme } from "./primitives/useChartTheme";

const fmtBRL = (v: number): string =>
  new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(v);

interface IFConeChartProps {
  readonly caminhoP10: [number, number][];
  readonly caminhoP50: [number, number][];
  readonly caminhoP90: [number, number][];
  readonly metaIf?: number;
  readonly "data-testid"?: string;
}

/** N3 — Cone de probabilidade Monte Carlo para IF.
 *
 * Três séries: P10 (cenário adverso), P50 (mediano), P90 (cenário favorável).
 * Linha horizontal opcional marcando a meta IF. P10 é o 10º percentil
 * (bottom 10% das simulações = menos patrimônio); P90 é o top 10%
 * (ADR-237 — paridade narrativa P10/P90 com convenção MC clássica).
 *
 * ADR-076 · Cores via `useChartTheme()` — resolve tokens semânticos em
 * runtime e re-calcula em dark mode. Sem RGB literal.
 */
export function IFConeConeChart({
  caminhoP10,
  caminhoP50,
  caminhoP90,
  metaIf,
  ...rest
}: IFConeChartProps) {
  const theme = useChartTheme();

  const { data } = useMemo<{
    labels: string[];
    data: ChartData<"line">;
  }>(() => {
    const lbls = caminhoP50.map(([ano]) => String(ano));

    const datasets: ChartData<"line">["datasets"] = [
      {
        label: "P10 — cenário adverso",
        data: caminhoP10.map(([, v]) => v),
        borderColor: theme.semantic.loss,
        backgroundColor: "transparent",
        fill: false,
        borderDash: [5, 4],
        borderWidth: 1.5,
        tension: 0.3,
        pointRadius: 0,
      },
      {
        label: "P50 — mediano",
        data: caminhoP50.map(([, v]) => v),
        borderColor: theme.primary,
        backgroundColor: "transparent",
        fill: false,
        borderWidth: 2,
        tension: 0.3,
        pointRadius: 0,
      },
      {
        label: "P90 — cenário favorável",
        data: caminhoP90.map(([, v]) => v),
        borderColor: theme.semantic.gain,
        backgroundColor: "transparent",
        fill: false,
        borderDash: [5, 4],
        borderWidth: 1.5,
        tension: 0.3,
        pointRadius: 0,
      },
    ];

    if (metaIf != null) {
      datasets.push({
        label: "Meta IF",
        data: lbls.map(() => metaIf),
        borderColor: theme.warning,
        backgroundColor: "transparent",
        fill: false,
        borderDash: [6, 3],
        borderWidth: 1.5,
        tension: 0,
        pointRadius: 0,
      });
    }

    return { labels: lbls, data: { labels: lbls, datasets } };
  }, [caminhoP10, caminhoP50, caminhoP90, metaIf, theme]);

  const options = useMemo<ChartOptions<"line">>(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "top" as const,
          labels: { boxWidth: 12, padding: 12 },
        },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.dataset.label}: ${fmtBRL(ctx.parsed.y ?? 0)}`,
          },
        },
      },
      scales: {
        x: {
          ticks: { maxTicksLimit: 10 },
          grid: { display: false },
        },
        y: {
          ticks: { callback: (v) => fmtBRL(Number(v)) },
        },
      },
    }),
    [],
  );

  return (
    <ChartCanvas
      type="line"
      data={data}
      options={options}
      ariaLabel="Cone de probabilidade Monte Carlo para independência financeira"
      data-testid={rest["data-testid"] ?? "if-cone-chart"}
    />
  );
}
