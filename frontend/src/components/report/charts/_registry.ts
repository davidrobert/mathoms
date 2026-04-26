/**
 * F9 · F2.A — Registry de charts migrados para React (Recharts).
 *
 * Cada lote adiciona entradas. Charts não presentes aqui ficam
 * omitidos na renderização (sem stub — o stub é por seção, não por chart).
 */
// Lote A (S1)
export { PatrimonioDoughnutChart } from "./PatrimonioDoughnutChart";
export { WaterfallIfChart } from "./WaterfallIfChart";
// `score_gauge` migrou para `ScoreCard` (ui/ScoreCard.tsx) em v2.E.7 — não é mais um chart Recharts.
// Lote B (S2)
export { FluxoMensalChart } from "./FluxoMensalChart";
export { ReceitaBarChart } from "./ReceitaBarChart";
export { DespesasDoughnutChart } from "./DespesasDoughnutChart";
export { ReceitaDespesaMensalChart } from "./ReceitaDespesaMensalChart";

export const MIGRATED_CHART_IDS = new Set([
  // Lote A
  "patrimonio_doughnut",
  "waterfall_if",
  // `score_gauge` removido — substituído pelo ScoreCard premium (v2.E.7).
  // Lote B
  "fluxo_mensal",
  "receita_bar",
  "despesas_doughnut",
  "receita_despesa_mensal",
]);
