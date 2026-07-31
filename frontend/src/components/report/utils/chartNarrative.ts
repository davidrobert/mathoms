/**
 * ADR-356 (A40.l4) — leitura única da conclusão de chart vinda do E5.N.
 *
 * Conclusões de chart vivem SEMPRE em `narrativas.charts[<id>]`: os 17 ids
 * que o produtor emite estão lá, e nenhum aparece no topo de `narrativas`.
 * Promovido de `S3InvestimentosSection` (onde era função local) para que o
 * padrão tenha uma casa nomeada — hoje o único call site é a própria S3
 * (as demais seções passam `narrativas.charts` inteiro ao
 * `NarrativeChartCard`). O que a promoção habilitou foi deletar as leituras
 * top-level mortas de S1/S2 sem deixar o padrão sem endereço.
 *
 * Gate estático (regra 5 de `dev/check_chart_conclusion_parity.py`) impede
 * que a leitura no topo de `narrativas` volte a aparecer em `sections/*.tsx`.
 */
export function readNarrativeConclusion(
  charts: Record<string, unknown> | undefined,
  chartId: string,
): string | null {
  const entry = charts?.[chartId] as { conclusion?: string } | undefined;
  const text = entry?.conclusion?.trim();
  return text && text.length > 0 ? text : null;
}
