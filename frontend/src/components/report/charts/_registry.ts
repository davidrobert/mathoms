/**
 * F9 · F2.A — Registry de charts migrados para React (Recharts).
 *
 * Cada lote adiciona entradas. Charts não presentes aqui ficam
 * omitidos na renderização (sem stub — o stub é por seção, não por chart).
 */
export { PatrimonioDoughnutChart } from "./PatrimonioDoughnutChart";
export { WaterfallIfChart } from "./WaterfallIfChart";
export { ScoreGaugeChart } from "./ScoreGaugeChart";

export const MIGRATED_CHART_IDS = new Set([
  "patrimonio_doughnut",
  "waterfall_if",
  "score_gauge",
]);
