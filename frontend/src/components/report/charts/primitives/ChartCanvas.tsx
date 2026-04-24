"use client";

import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import type { Chart as ChartJS, ChartOptions, ChartType, ChartData } from "chart.js";
import { Chart as ReactChart } from "react-chartjs-2";
import { ensureChartRegistered } from "./ChartRegistry";

ensureChartRegistered();

/** ADR-117 · Fase 2 — wrapper base para todos primitivos de chart.
 *
 * Responsabilidades:
 *  - registro Chart.js (via ChartRegistry)
 *  - aspect-ratio + min/max height
 *  - print fallback (canvas → PNG img no 1º render, visível em @media print)
 *  - data-testid hook
 *
 * API intencionalmente fina: cada primitivo específico (ChartBar/Donut/…)
 * envelopa este componente e fornece `type`, `data`, `options` formatados.
 */
export interface ChartCanvasProps<TType extends ChartType = ChartType> {
  readonly type: TType;
  readonly data: ChartData<TType>;
  readonly options?: ChartOptions<TType>;
  readonly height?: number | "auto";
  readonly minHeight?: number;
  readonly maxHeight?: number;
  readonly className?: string;
  readonly "data-testid"?: string;
  readonly ariaLabel?: string;
}

export function ChartCanvas<TType extends ChartType = ChartType>({
  type,
  data,
  options,
  height = "auto",
  minHeight = 250,
  maxHeight = 400,
  className,
  ariaLabel,
  ...rest
}: ChartCanvasProps<TType>) {
  const chartRef = useRef<ChartJS | null>(null);
  const [printSrc, setPrintSrc] = useState<string | null>(null);

  useEffect(() => {
    const c = chartRef.current;
    if (!c) return;
    const timer = window.setTimeout(() => {
      try {
        setPrintSrc(c.toBase64Image());
      } catch {
        // ignore — canvas tainted ou contexto perdido
      }
    }, 300);
    return () => window.clearTimeout(timer);
  }, [data]);

  const style = useMemo<CSSProperties>(
    () => ({
      minHeight,
      maxHeight: height === "auto" ? maxHeight : undefined,
      height: typeof height === "number" ? height : undefined,
      position: "relative",
      width: "100%",
    }),
    [height, minHeight, maxHeight],
  );

  return (
    <div
      className={className}
      style={style}
      data-chart-canvas
      data-testid={rest["data-testid"]}
    >
      <ReactChart
        ref={(instance) => {
          // react-chartjs-2 retorna `ChartJSOrUndefined`; narrow para `Chart | null`
          chartRef.current = (instance as ChartJS | undefined) ?? null;
        }}
        type={type}
        data={data as ChartData}
        options={options as ChartOptions}
        aria-label={ariaLabel}
        role="img"
      />
      {printSrc && (
        <img
          src={printSrc}
          alt={ariaLabel ?? ""}
          className="chart-print-img"
          aria-hidden="true"
        />
      )}
    </div>
  );
}
