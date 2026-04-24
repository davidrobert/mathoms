/** ADR-117 · Fase 2 — tipos compartilhados entre primitivos de chart. */

export type PeriodWindow = "3m" | "6m" | "12m" | "ytd" | "all";

export interface ChartSeriesPoint {
  readonly x: string | number;
  readonly y: number;
}

export interface ChartCategoricalDatum {
  readonly label: string;
  readonly value: number;
  /** Override explícito de cor. Se omitido, cai na palette categórica. */
  readonly color?: string;
}

export interface ChartSeries {
  readonly label: string;
  readonly data: readonly number[];
  readonly color?: string;
}

export interface ChartBaseProps {
  readonly title?: string;
  readonly subtitle?: string;
  readonly conclusion?: string;
  readonly height?: number | "auto";
  readonly "data-testid"?: string;
  readonly ariaLabel?: string;
  readonly periodWindow?: PeriodWindow;
  readonly onPeriodChange?: (w: PeriodWindow) => void;
}
