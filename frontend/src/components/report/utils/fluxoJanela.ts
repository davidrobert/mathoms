/** ADR-306 D1 (A40.l3) — janela canônica de mensalização do fluxo de caixa.
 *
 * D1 divide o payload em duas famílias: **mensalização** (ratios/KPIs/médias
 * por mês) lê a janela de 12 meses documentados; **agregado histórico**
 * (composição, totais) pode usar full-period, mas **apenas rotulado**. Este
 * seletor resolve a primeira família num único lugar — 3 call sites liam os
 * mesmos 2 campos do bloco errado (`buildContext` do chart, builder
 * `fluxo_mensal`, `SECTION_SUMMARIES.S2`).
 *
 * **Invariante do módulo:** nenhuma função aqui devolve valor de um bloco com
 * rótulo de outro. O rótulo é lido do MESMO objeto de onde o valor saiu, na
 * mesma expressão. Quando o bloco não declara base, o resultado é `null` ou o
 * rótulo do bloco efetivamente lido — nunca um rótulo herdado do vizinho.
 * A regressão que motiva o invariante: um ramo de degradação devolvia
 * `total_pontuais` (acumulado de todo o período) carregando o rótulo `12m` do
 * campo `janela` vizinho — valor full sob rótulo de janela, que é o próprio
 * defeito que esta lane fecha.
 *
 * Aceita `unknown` porque `ReportAnalysisData.fluxo_caixa` é
 * `Record<string, unknown>` no contrato HTTP e `FluxoCaixaSummary` nos
 * componentes — um narrow, dois consumidores.
 */
import { parseJanelaRotulo, type JanelaRotulo } from "./janelaLabel";

/** Rótulo do agregado histórico. `meses: undefined` é deliberado: nenhum bloco
 * do payload declara quantos meses o acumulado full cobre — `janela_meses` de
 * `consumo_consciente` conta os meses da janela da FOLGA, e importá-lo de
 * `fluxo_caixa` seria inferência cross-bloco, o oposto do invariante acima. */
const HISTORICO: JanelaRotulo = {
  tipo: "full",
  anoIrpf: undefined,
  meses: undefined,
};

/** Base de um agregado histórico lido de `bloco`: o rótulo que o PRÓPRIO bloco
 * declara, senão `full` sem contagem (nenhum outro campo descreve o acumulado —
 * inferir de vizinho é o defeito).
 *
 * Existe para o consumidor que soma um snapshot de bloco inteiro (ex.: o
 * fallback `despesas_por_categoria` do donut, quando `despesa_datasets` está
 * ausente): sem isto o call site imprimia o range da janela renderizada ao lado
 * de um total de todo o período. */
export function resolveRotuloAgregado(bloco: unknown): JanelaRotulo {
  if (bloco == null || typeof bloco !== "object") return HISTORICO;
  const campos = bloco as Record<string, unknown>;
  return parseJanelaRotulo(campos.janela, campos.janela_meses) ?? HISTORICO;
}

/** Par indissociável (valor, base). Existe como tipo para que o call site não
 * consiga imprimir o número sem o rótulo que o acompanha. */
export interface ValorComJanela {
  readonly valor: number | undefined;
  readonly rotulo: JanelaRotulo;
}

/** Resultado do seletor de mensalização. `rotulo` vem do **campo** `janela` do
 * bloco lido — D2 criou esse campo justamente para a UI não inferir a base a
 * partir de onde o número estava. */
export interface FluxoJanelaMensal {
  readonly receitaRecorrenteMensal: number;
  readonly despesaMensalMedia: number;
  /** Canônica ex-aporte (ADR-333). `undefined` no bloco `full`, que não emite
   * o campo — omita a taxa em vez de recomputar de `despesa_mensal_media`. */
  readonly taxaPoupancaRecorrentePct: number | undefined;
  readonly rotulo: JanelaRotulo;
}

function numberAt(bloco: unknown, key: string): number | undefined {
  if (bloco == null || typeof bloco !== "object") return undefined;
  const value = (bloco as Record<string, unknown>)[key];
  return typeof value === "number" && Number.isFinite(value)
    ? value
    : undefined;
}

/** Percentual aceita numeric string. O substrato versionado emite
 * `ratios.taxa_poupanca_recorrente_pct: "50.000000"` — campo derivado de
 * `Decimal` sem `PlainSerializer` serializa como string, e uma guarda estrita
 * deixaria cair em silêncio justamente o KPI comportamental do relatório.
 * Coerção restrita a percentual: monetário segue estrito (ADR-090). */
function pctAt(bloco: unknown, key: string): number | undefined {
  if (bloco == null || typeof bloco !== "object") return undefined;
  const value = (bloco as Record<string, unknown>)[key];
  if (typeof value === "number")
    return Number.isFinite(value) ? value : undefined;
  if (typeof value !== "string" || value.trim() === "") return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

/** Rótulo declarado no bloco; sem ele, a posição do bloco é a única evidência
 * da base (payload pré-A28). */
function rotuloDoBloco(
  bloco: unknown,
  fallbackTipo: "12m" | "full",
): JanelaRotulo {
  const campos = (bloco ?? {}) as Record<string, unknown>;
  return (
    parseJanelaRotulo(campos.janela, campos.janela_meses) ?? {
      tipo: fallbackTipo,
      anoIrpf: undefined,
      meses: numberAt(bloco, "janela_meses") ?? numberAt(bloco, "n_meses"),
    }
  );
}

function readBloco(
  bloco: unknown,
  fallbackTipo: "12m" | "full",
): FluxoJanelaMensal | null {
  const receita = numberAt(bloco, "receita_recorrente_mensal");
  const despesa = numberAt(bloco, "despesa_mensal_media");
  if (receita === undefined || despesa === undefined) return null;
  return {
    receitaRecorrenteMensal: receita,
    despesaMensalMedia: despesa,
    taxaPoupancaRecorrentePct: pctAt(bloco, "taxa_poupanca_recorrente"),
    rotulo: rotuloDoBloco(bloco, fallbackTipo),
  };
}

/** Bloco `janela_12m` quando presente e completo; senão degrada para o
 * top-level rotulado `full`. `null` quando nenhum dos dois traz os 2 campos.
 *
 * `fallbackTipo` só entra em payload pré-A28 sem o campo `janela`: aí a
 * posição do bloco é a única evidência da base. */
export function resolveFluxoJanelaMensal(
  fluxo: unknown,
): FluxoJanelaMensal | null {
  if (fluxo == null || typeof fluxo !== "object") return null;
  const bloco12m = (fluxo as Record<string, unknown>).janela_12m;
  return readBloco(bloco12m, "12m") ?? readBloco(fluxo, "full");
}

/** Leitura de `consumo_consciente` (ADR-306 D1 + D6). Duas bases coexistem no
 * mesmo card e o seletor as devolve **já emparelhadas com o próprio rótulo**:
 *
 * - `historico`/`equivalente` — inventário acumulado, D6 ("`total_pontuais`
 *   **(tabela)** segue full-period"). Rótulo sempre `HISTORICO`, porque o campo
 *   `janela` deste bloco descreve a janela da FOLGA, não a do total.
 * - `rotuloFolga` — base de `folga_mensal`/`folga_pct`/`teto_sugerido`, que o
 *   E5 deriva da janela canônica (D1). `null` sem declaração: sem rótulo
 *   inventado.
 *
 * A troca do KPI de pontuais para a base de janela (+ ritmo mensal) é mudança
 * de domínio no que a família vê e saiu para a lane A40.l15 — aqui o par
 * (valor, rótulo) é o full rotulado, coerente com a prosa do E5. */
export interface ConsumoBases {
  readonly historico: ValorComJanela;
  readonly equivalente: ValorComJanela;
  readonly rotuloFolga: JanelaRotulo | null;
}

export function resolveConsumoBases(consumo: unknown): ConsumoBases | null {
  if (consumo == null || typeof consumo !== "object") return null;
  const bloco = consumo as Record<string, unknown>;
  return {
    historico: { valor: numberAt(bloco, "total_pontuais"), rotulo: HISTORICO },
    equivalente: {
      valor: numberAt(bloco, "equivalente_meses_aporte"),
      rotulo: HISTORICO,
    },
    rotuloFolga: parseJanelaRotulo(bloco.janela, bloco.janela_meses),
  };
}

/** Taxa de poupança do bloco `ratios` com a base que o próprio bloco declara.
 * Existe para que o hero não consiga imprimir o percentual sem o rótulo: o
 * defeito medido era `formatJanelaTooltip(ratios.janela_referencia, …)`, que
 * recebia a string de PERÍODO ("2026-01 a 2026-01") no lugar do vocabulário
 * D2 e rotulava a base com um intervalo. */
export interface TaxaPoupancaComJanela {
  readonly recorrentePct: number | undefined;
  readonly totalPct: number | undefined;
  readonly rotulo: JanelaRotulo | null;
}

export function resolveTaxaPoupanca(
  ratios: unknown,
): TaxaPoupancaComJanela | null {
  if (ratios == null || typeof ratios !== "object") return null;
  const bloco = ratios as Record<string, unknown>;
  return {
    recorrentePct: pctAt(bloco, "taxa_poupanca_recorrente_pct"),
    totalPct: pctAt(bloco, "taxa_poupanca_total_pct"),
    rotulo: parseJanelaRotulo(bloco.janela, bloco.janela_meses ?? bloco.janela_n_meses),
  };
}
