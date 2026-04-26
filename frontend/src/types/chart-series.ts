/**
 * Onda v2.E.2 · Report Premium UI — DTO de série de chart (wire shape).
 *
 * Forma serializada que o backend (E5) emite em
 * `receita_despesa_mensal_detalhado.{receita_datasets,despesa_datasets}`
 * a partir de `pipeline/domain/services/fluxo_caixa_enricher.py`.
 *
 * Estado atual do backend (`fluxo_caixa_enricher.py:291-313`): emite apenas
 * `{label, data}`. `backgroundColor`, `stack` e `borderRadius` são campos
 * opcionais reservados para o consumo Chart.js — frontend pode preencher
 * client-side ou o backend pode passar a emitir no futuro (ondas v2.E.4-6).
 *
 * NOTA: O tipo `ChartSeries` em
 * `@/components/report/charts/primitives/types` é diferente — aquele é a
 * API interna dos primitives de chart (usa `color`); este é o DTO do wire.
 * Não fundir: shapes representam camadas distintas.
 */

export interface ChartSeries {
  readonly label: string;
  readonly data: readonly number[];
  readonly backgroundColor?: string;
  readonly stack?: "receita" | "despesa";
  readonly borderRadius?: number;
}
