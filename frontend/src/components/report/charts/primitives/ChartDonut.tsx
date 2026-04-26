"use client";

import { useMemo } from "react";
import type { ChartData, ChartOptions } from "chart.js";
import { ChartCanvas } from "./ChartCanvas";
import { useChartTheme } from "./useChartTheme";
import type { ChartBaseProps, ChartCategoricalDatum } from "./types";

export interface ChartDonutProps extends ChartBaseProps {
  readonly data: readonly ChartCategoricalDatum[];
  readonly cutout?: string | number;
  readonly showDataLabels?: boolean;
  readonly formatValue?: (v: number) => string;
  /** Override do label exibido no segmento. Recebe (valor, pct, label). Se
   *  retornar string vazia, datalabel é omitido. Default: `${pct}%` se ≥ 5%. */
  readonly dataLabelFormatter?: (
    value: number,
    pct: number,
    label: string,
  ) => string;
  /** Texto central (renderizado via div absoluta, não via plugin). */
  readonly centerLabel?: string;
  readonly centerValue?: string;
}

const BRL = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 0,
});

export function ChartDonut({
  data,
  cutout = "60%",
  showDataLabels = false,
  formatValue = (v) => BRL.format(v),
  dataLabelFormatter,
  centerLabel,
  centerValue,
  height = "auto",
  ariaLabel,
  ...rest
}: ChartDonutProps) {
  const theme = useChartTheme();

  const chartData = useMemo<ChartData<"doughnut">>(
    () => ({
      labels: data.map((d) => d.label),
      datasets: [
        {
          data: data.map((d) => d.value),
          backgroundColor: data.map(
            (d, i) => d.color ?? theme.categorical[i % theme.categorical.length],
          ),
          borderColor: theme.surface,
          borderWidth: 2,
        },
      ],
    }),
    [data, theme.categorical, theme.surface],
  );

  const options = useMemo<ChartOptions<"doughnut">>(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      cutout,
      plugins: {
        legend: { position: "bottom", labels: { color: theme.text } },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.label}: ${formatValue(Number(ctx.parsed))}`,
          },
        },
        datalabels: showDataLabels
          ? {
              display: true,
              color: "#fff",
              font: { weight: 600 },
              textStrokeColor: "rgba(0,0,0,0.3)",
              textStrokeWidth: 2,
              formatter: (v: number, ctx) => {
                const total = (ctx.dataset.data as number[]).reduce((a, b) => a + b, 0);
                const pct = total > 0 ? (v / total) * 100 : 0;
                if (dataLabelFormatter) {
                  const lbl = String(ctx.chart.data.labels?.[ctx.dataIndex] ?? "");
                  return dataLabelFormatter(v, pct, lbl);
                }
                return pct >= 5 ? `${pct.toFixed(0)}%` : "";
              },
            }
          : { display: false },
      },
    }),
    [cutout, showDataLabels, theme, formatValue, dataLabelFormatter],
  );

  return (
    <div style={{ position: "relative", width: "100%" }}>
      <ChartCanvas
        type="doughnut"
        data={chartData}
        options={options}
        height={height}
        ariaLabel={ariaLabel ?? rest.title}
        data-testid={rest["data-testid"]}
      />
      {(centerLabel || centerValue) && (
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            textAlign: "center",
            pointerEvents: "none",
          }}
          aria-hidden="true"
        >
          {centerValue && (
            <div
              style={{
                fontFamily: "var(--font-display)",
                fontSize: "var(--report-font-size-xl, 22px)",
                fontWeight: 800,
                color: "var(--brand-primary)",
              }}
            >
              {centerValue}
            </div>
          )}
          {centerLabel && (
            <div
              style={{
                fontSize: "var(--report-font-size-sm, 12px)",
                color: "var(--surface-muted-foreground)",
                marginTop: 2,
              }}
            >
              {centerLabel}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/** Pie chart — atalho para ChartDonut com cutout=0. */
export function ChartPie(props: Omit<ChartDonutProps, "cutout">) {
  return <ChartDonut {...props} cutout={0} />;
}
