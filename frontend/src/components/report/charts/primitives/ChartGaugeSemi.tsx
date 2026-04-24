"use client";

import { useMemo } from "react";
import type { ChartData, ChartOptions } from "chart.js";
import { ChartCanvas } from "./ChartCanvas";
import { useChartTheme } from "./useChartTheme";
import type { ChartBaseProps } from "./types";

export interface ChartGaugeSemiProps extends ChartBaseProps {
  /** Valor atual (0..max). */
  readonly value: number;
  /** Escala máxima. Default 100. */
  readonly max?: number;
  /** Cor da porção preenchida. Se omitido, deriva do valor via tresholds. */
  readonly fillColor?: string;
  readonly trackColor?: string;
  /** Label central grande (ex: "8.2"). */
  readonly centerValue?: string;
  /** Label central pequeno (ex: "Score"). */
  readonly centerLabel?: string;
  /** Thresholds para colorir automaticamente: [ruim, medio, bom]. Default [3, 6, 8]. */
  readonly thresholds?: readonly [number, number, number];
}

/**
 * Gauge semi-circular — doughnut com rotation:-90° + circumference:180°.
 * Matching `#chart-score-gauge` do exemplar.
 */
export function ChartGaugeSemi({
  value,
  max = 100,
  fillColor,
  trackColor,
  centerValue,
  centerLabel,
  thresholds = [3, 6, 8],
  height = 260,
  ariaLabel,
  ...rest
}: ChartGaugeSemiProps) {
  const theme = useChartTheme();

  const resolvedFill = useMemo(() => {
    if (fillColor) return fillColor;
    const [low, mid, high] = thresholds;
    const scaled = (value / max) * 10; // normaliza para a escala de thresholds (0-10)
    if (scaled < low) return theme.danger;
    if (scaled < mid) return theme.warning;
    if (scaled < high) return theme.info;
    return theme.accent;
  }, [fillColor, thresholds, value, max, theme]);

  const data = useMemo<ChartData<"doughnut">>(() => {
    const clamped = Math.max(0, Math.min(max, value));
    return {
      labels: ["valor", "restante"],
      datasets: [
        {
          data: [clamped, max - clamped],
          backgroundColor: [resolvedFill, trackColor ?? theme.border],
          borderWidth: 0,
          circumference: 180,
          rotation: -90,
        },
      ],
    };
  }, [value, max, resolvedFill, trackColor, theme.border]);

  const options = useMemo<ChartOptions<"doughnut">>(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      cutout: "75%",
      plugins: {
        legend: { display: false },
        tooltip: { enabled: false },
      },
    }),
    [],
  );

  return (
    <div style={{ position: "relative", width: "100%" }}>
      <ChartCanvas
        type="doughnut"
        data={data}
        options={options}
        height={height}
        ariaLabel={ariaLabel ?? rest.title ?? `Gauge ${value} de ${max}`}
        data-testid={rest["data-testid"]}
      />
      {(centerValue || centerLabel) && (
        <div
          style={{
            position: "absolute",
            top: "68%",
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
                fontSize: "var(--report-font-size-2xl, 28px)",
                fontWeight: 800,
                color: resolvedFill,
                lineHeight: 1,
              }}
            >
              {centerValue}
            </div>
          )}
          {centerLabel && (
            <div
              style={{
                fontSize: "var(--report-font-size-xs, 10px)",
                color: "var(--surface-muted-foreground)",
                marginTop: 4,
                textTransform: "uppercase",
                letterSpacing: "0.5px",
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
