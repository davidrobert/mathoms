"use client";

import { useMemo } from "react";
import type { ChartData, ChartOptions } from "chart.js";
import { ChartCanvas } from "./primitives/ChartCanvas";

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
 * Três séries: P10 (otimista), P50 (mediano), P90 (conservador).
 * Linha horizontal opcional marcando a meta IF.
 */
export function IFConeConeChart({
  caminhoP10,
  caminhoP50,
  caminhoP90,
  metaIf,
  ...rest
}: IFConeChartProps) {
  const { labels, data } = useMemo<{
    labels: string[];
    data: ChartData<"line">;
  }>(() => {
    const lbls = caminhoP50.map(([ano]) => String(ano));

    const datasets: ChartData<"line">["datasets"] = [
      {
        label: "P10 — otimista",
        data: caminhoP10.map(([, v]) => v),
        borderColor: "rgba(34,197,94,0.85)",
        backgroundColor: "rgba(34,197,94,0.08)",
        fill: false,
        borderDash: [5, 4],
        borderWidth: 1.5,
        tension: 0.3,
        pointRadius: 0,
      },
      {
        label: "P50 — mediano",
        data: caminhoP50.map(([, v]) => v),
        borderColor: "rgba(59,130,246,1)",
        backgroundColor: "transparent",
        fill: false,
        borderWidth: 2,
        tension: 0.3,
        pointRadius: 0,
      },
      {
        label: "P90 — conservador",
        data: caminhoP90.map(([, v]) => v),
        borderColor: "rgba(239,68,68,0.85)",
        backgroundColor: "rgba(239,68,68,0.08)",
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
        borderColor: "rgba(251,191,36,0.9)",
        backgroundColor: "transparent",
        fill: false,
        borderDash: [6, 3],
        borderWidth: 1.5,
        tension: 0,
        pointRadius: 0,
      });
    }

    return { labels: lbls, data: { labels: lbls, datasets } };
  }, [caminhoP10, caminhoP50, caminhoP90, metaIf]);

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
