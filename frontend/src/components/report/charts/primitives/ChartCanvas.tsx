"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import type { Chart as ChartJS, ChartOptions, ChartType, ChartData } from "chart.js";
import { Chart as ReactChart } from "react-chartjs-2";
import { CHART_RENDERED_EVENT, ensureChartRegistered } from "./ChartRegistry";

ensureChartRegistered();

/** Silêncio de render que conta como "desenho terminou". Acima de um frame
 * (~16ms) para não disparar no meio da animação, e curto o bastante para o
 * `pdf_renderer` (que espera 2s após o ready) já achar a imagem pronta. */
const PRINT_SNAPSHOT_QUIET_MS = 250;

/** Serializa o canvas para o `<img>` que o PDF renderiza — quando o desenho para.
 *
 * `report-print.css` esconde o `<canvas>` em `@media print` e mostra este PNG,
 * então ele **é** o gráfico no papel. O `setTimeout(…, 300)` que existia aqui
 * congelava o frame de 300ms de uma animação de ~1s: a barra de "Salário" saía
 * com 81% do comprimento e a rosca saía aberta, contradizendo o número impresso
 * ao lado (A40.l53). Esperar um tempo maior não resolve — o desenho recomeça a
 * cada resize, inclusive o que a captura do Playwright provoca.
 */
function usePrintSnapshot(
  chartRef: { current: ChartJS | null },
  data: unknown,
): string | null {
  const [printSrc, setPrintSrc] = useState<string | null>(null);
  useEffect(() => {
    const chart = chartRef.current;
    const canvas = chart?.canvas;
    if (!chart || !canvas) return;
    let timer = 0;
    const capture = () => {
      try {
        setPrintSrc(chart.toBase64Image());
      } catch {
        // ignore — canvas tainted ou contexto perdido
      }
    };
    const agendar = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(capture, PRINT_SNAPSHOT_QUIET_MS);
    };
    canvas.addEventListener(CHART_RENDERED_EVENT, agendar);
    agendar();
    return () => {
      canvas.removeEventListener(CHART_RENDERED_EVENT, agendar);
      window.clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);
  return printSrc;
}

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
  /** v2.E.6 — Callback que recebe a instância Chart.js para uso imperativo
   * (ex.: legenda custom que faz toggle via `getDatasetMeta`). Mantém o
   * primitive controlado — quem precisa de acesso passa o callback. */
  readonly onChartReady?: (chart: ChartJS | null) => void;
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
  onChartReady,
  ...rest
}: ChartCanvasProps<TType>) {
  const chartRef = useRef<ChartJS | null>(null);

  // Ref callback estavel — React chama com null em unmount; estabilidade
  // evita disparar setState do consumer (`onChartReady`) a cada render.
  const setRef = useCallback(
    (instance: unknown) => {
      const chart = (instance as ChartJS | undefined) ?? null;
      if (chartRef.current === chart) return;
      chartRef.current = chart;
      onChartReady?.(chart);
    },
    [onChartReady],
  );

  const printSrc = usePrintSnapshot(chartRef, data);

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
        ref={setRef}
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
          style={{ display: "none" }}
        />
      )}
    </div>
  );
}
