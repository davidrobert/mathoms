/** A28.l9 + A40.l3 — vocabulário de janela de mensalização (ADR-306 D2).
 *
 * D2 fecha o vocabulário em `12m` | `full` | `irpf[_<ano>]` e exige a chave
 * irmã `janela_meses` (meses documentados reais). Este módulo é o **único**
 * lugar que interpreta esse par: consumidores recebem um valor tipado e nunca
 * inspecionam a string crua.
 *
 * Por que um parser em vez de `string`: o payload real emite, no MESMO bloco,
 * `janela: "12m"` e `janela_referencia: "2026-01 a 2026-01"` (string de
 * período, `ratios_calculator.py:205`). Consumidor que aceitasse qualquer
 * string renderizava `a janela "2026-01 a 2026-01"` como se fosse rótulo de
 * base — passava na fixture e quebrava em produção. Fora do vocabulário ⇒
 * `null` ⇒ nenhum rótulo inventado.
 */

export type JanelaTipo = "12m" | "full" | "irpf";

export interface JanelaRotulo {
  readonly tipo: JanelaTipo;
  /** Ano-base quando `tipo === "irpf"`. */
  readonly anoIrpf: string | undefined;
  /** Meses documentados reais (D2). `undefined` quando o payload não declara. */
  readonly meses: number | undefined;
}

const IRPF_RE = /^irpf(?:_(\d{4}))?$/;

function mesesAt(value: unknown): number | undefined {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) return undefined;
  return Math.trunc(value);
}

/** `null` para payload sem rótulo (pré-A28) **e** para string fora do
 * vocabulário D2 — as duas situações pedem silêncio, não rótulo adivinhado. */
export function parseJanelaRotulo(janela: unknown, janelaMeses?: unknown): JanelaRotulo | null {
  if (typeof janela !== "string" || janela.length === 0) return null;
  const meses = mesesAt(janelaMeses);
  if (janela === "12m" || janela === "full") return { tipo: janela, anoIrpf: undefined, meses };
  const irpf = IRPF_RE.exec(janela);
  if (irpf) return { tipo: "irpf", anoIrpf: irpf[1], meses };
  return null;
}

/** Plural do substantivo isolado ("12 meses", "1 mês"). Use apenas onde não há
 * artigo nem particípio para concordar — para a cláusula de janela use
 * `describeMesesDocumentados`, que concorda a frase inteira. */
export function pluralMeses(n: number): string {
  return n === 1 ? "mês" : "meses";
}

/** Cláusula de meses documentados com artigo, numeral e particípio concordados
 * de uma vez.
 *
 * `pluralMeses` sozinho concordava só o substantivo e rendia "os últimos 1 mês
 * documentados" — e `janela_meses = 1` é o valor do substrato versionado
 * (`backend/tests/snapshots/dogfood_view_model.json`: `ratios.janela_meses`,
 * `fluxo_caixa.janela_12m.n_meses` e `consumo_consciente.janela_meses` são
 * todos 1). Bug alimentado por dado, não hipótese. */
export function describeMesesDocumentados(n: number): string {
  return n === 1 ? "o último mês documentado" : `os últimos ${n} meses documentados`;
}

/** Cláusula de escopo temporal para prosa ("sobre …", "em …"). */
export function describeJanelaEscopo(rotulo: JanelaRotulo): string {
  if (rotulo.tipo === "12m") {
    return describeMesesDocumentados(rotulo.meses ?? 12);
  }
  if (rotulo.tipo === "irpf") {
    return `o ano-base IRPF${rotulo.anoIrpf ? ` ${rotulo.anoIrpf}` : ""}`;
  }
  const sufixo = rotulo.meses ? ` (${rotulo.meses} ${pluralMeses(rotulo.meses)})` : "";
  return `todo o período analisado${sufixo}`;
}

/** Mesma cláusula com a preposição contraída ("**nos** últimos 12 meses",
 * "**no** último mês", "**em** todo o período"). Concatenar
 * `"em " + describeJanelaEscopo()` produzia "em os últimos 12 meses" — medido
 * no DOM renderizado. */
export function describeJanelaEm(rotulo: JanelaRotulo): string {
  const escopo = describeJanelaEscopo(rotulo);
  if (escopo.startsWith("os ")) return `nos ${escopo.slice(3)}`;
  if (escopo.startsWith("o ")) return `no ${escopo.slice(2)}`;
  return `em ${escopo}`;
}

/** Rótulo curto para imprimir ao lado de um número (I5: tooltip não imprime
 * no PDF, e o PDF é o artefato que a família guarda). */
export function janelaBadgeLabel(rotulo: JanelaRotulo | null): string | null {
  if (!rotulo) return null;
  if (rotulo.tipo === "12m") {
    const meses = rotulo.meses ?? 12;
    return meses === 1 ? "último mês documentado" : `últimos ${meses} meses documentados`;
  }
  if (rotulo.tipo === "irpf") {
    return `ano-base IRPF${rotulo.anoIrpf ? ` ${rotulo.anoIrpf}` : ""}`;
  }
  return rotulo.meses
    ? `todo o período · ${rotulo.meses} ${pluralMeses(rotulo.meses)}`
    : "todo o período documentado";
}

/** Tooltip de valor **mensalizado** (média por mês). Complementa o rótulo
 * impresso — nunca o substitui (ADR-306 §Emenda A40.l3: tooltip não imprime). */
export function formatJanelaTooltip(rotulo: JanelaRotulo | null): string | null {
  if (!rotulo) return null;
  if (rotulo.tipo === "irpf") {
    return `Valor mensalizado do ano-base IRPF${rotulo.anoIrpf ? ` ${rotulo.anoIrpf}` : ""} (12 meses).`;
  }
  return `Média mensal calculada sobre ${describeJanelaEscopo(rotulo)}.`;
}
