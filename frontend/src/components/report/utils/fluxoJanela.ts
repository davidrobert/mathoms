/** ADR-306 D1 (A40.l3) — janela canônica de mensalização do fluxo de caixa.
 *
 * D1 divide o payload em duas famílias: **mensalização** (ratios/KPIs/médias
 * por mês) lê a janela de 12 meses documentados; **agregado histórico**
 * (composição, totais) pode usar full-period, mas **apenas rotulado**. Este
 * seletor resolve a primeira família num único lugar — 4 call sites liam os
 * mesmos 2 campos do bloco errado (`buildContext`, `buildFallbackConclusion`,
 * builder `fluxo_mensal`, `SECTION_SUMMARIES.S2`).
 *
 * Aceita `unknown` porque `ReportAnalysisData.fluxo_caixa` é
 * `Record<string, unknown>` no contrato HTTP e `FluxoCaixaSummary` nos
 * componentes — um narrow, dois consumidores.
 */

/** Resultado do seletor. `janela` diz de qual bloco os números vieram — o
 * call site é obrigado a rotular (nunca número full sob rótulo 12m). */
export interface FluxoJanelaMensal {
  readonly receitaRecorrenteMensal: number;
  readonly despesaMensalMedia: number;
  /** `receita − despesa` (por mês). **Não** é `fluxo_liquido`, que é o total
   * do intervalo — na fixture de contrato, 11.000 contra 228.000. */
  readonly sobraMensal: number;
  /** Canônica ex-aporte (ADR-333). `undefined` no bloco `full`, que não emite
   * o campo — omita a taxa em vez de recomputar de `despesa_mensal_media`. */
  readonly taxaPoupancaRecorrentePct: number | undefined;
  readonly janela: "12m" | "full";
  readonly janelaMeses: number | undefined;
}

function numberAt(bloco: unknown, key: string): number | undefined {
  if (bloco == null || typeof bloco !== "object") return undefined;
  const value = (bloco as Record<string, unknown>)[key];
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function readBloco(bloco: unknown, janela: "12m" | "full"): FluxoJanelaMensal | null {
  const receita = numberAt(bloco, "receita_recorrente_mensal");
  const despesa = numberAt(bloco, "despesa_mensal_media");
  if (receita === undefined || despesa === undefined) return null;
  return {
    receitaRecorrenteMensal: receita,
    despesaMensalMedia: despesa,
    sobraMensal: receita - despesa,
    taxaPoupancaRecorrentePct: numberAt(bloco, "taxa_poupanca_recorrente"),
    janela,
    janelaMeses: numberAt(bloco, "janela_meses") ?? numberAt(bloco, "n_meses"),
  };
}

/** Bloco `janela_12m` quando presente e completo; senão degrada para o
 * top-level rotulado `full`. `null` quando nenhum dos dois traz os 2 campos. */
export function resolveFluxoJanelaMensal(fluxo: unknown): FluxoJanelaMensal | null {
  if (fluxo == null || typeof fluxo !== "object") return null;
  const bloco12m = (fluxo as Record<string, unknown>).janela_12m;
  return readBloco(bloco12m, "12m") ?? readBloco(fluxo, "full");
}

/** Cláusula de escopo temporal para prosa. Sempre rotula — é a obrigação que
 * ADR-306 §Consequências impõe à UI. */
export function describeJanelaEscopo(janela: FluxoJanelaMensal): string {
  if (janela.janela === "12m") {
    return `os últimos ${janela.janelaMeses ?? 12} meses documentados`;
  }
  const sufixo = janela.janelaMeses ? ` (${janela.janelaMeses} meses)` : "";
  return `todo o período analisado${sufixo}`;
}
