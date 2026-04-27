/** ADR-117 · Fase 2 — barrel de primitivos de chart (Chart.js).
 *
 * Consumidores devem importar daqui:
 *   import { ChartBar, ChartDonut, ChartConclusion } from "@/components/report/charts/primitives";
 *
 * Para charts concretos (PatrimonioDoughnutChart, etc.) ver
 * frontend/src/components/report/charts/_registry.ts (Recharts legado, migração gradual).
 */
export { ChartCanvas } from "./ChartCanvas";
export type { ChartCanvasProps } from "./ChartCanvas";

export { ChartBar, ChartStackedBar } from "./ChartBar";
export type { ChartBarProps } from "./ChartBar";

export { ChartDonut, ChartPie } from "./ChartDonut";
export type { ChartDonutProps } from "./ChartDonut";

export { ChartLine } from "./ChartLine";
export type { ChartLineProps } from "./ChartLine";

export { ChartCombo } from "./ChartCombo";
export type { ChartComboProps, ChartComboSeries } from "./ChartCombo";

export { ChartWaterfall } from "./ChartWaterfall";
export type { ChartWaterfallProps, WaterfallStep } from "./ChartWaterfall";

export { ChartGaugeSemi } from "./ChartGaugeSemi";
export type { ChartGaugeSemiProps } from "./ChartGaugeSemi";

export { ChartConclusion } from "./ChartConclusion";
export { ChartNav } from "./ChartNav";
export type { ChartNavProps } from "./ChartNav";

export { useChartTheme } from "./useChartTheme";
export type { ChartPalette, ChartSemanticPalette } from "./useChartTheme";

export { ensureChartRegistered } from "./ChartRegistry";

export type {
  ChartBaseProps,
  ChartCategoricalDatum,
  ChartSeries,
  ChartSeriesPoint,
  PeriodWindow,
} from "./types";
