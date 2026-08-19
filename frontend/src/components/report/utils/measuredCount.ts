/** PD-6 (RV6-22) — contagem que distingue "medi e deu zero" de "não medi".
 *
 * Os contadores client-side do banner de qualidade nasceram `number` com
 * `catch (() => {})` sobre `useState(0)`: falha de fetch ficava byte-idêntica a
 * zero medido, e o relatório afirmava "sem pendências" sobre um número que
 * nunca chegou. Corrigir só a UI fecharia a instância; enquanto o TIPO colapsar
 * os dois estados, o próximo consumidor repete o bug — por isso a distinção
 * mora aqui, não no componente.
 *
 * Polaridade POSITIVA, como `mayAssertCleanQuality` ([[ADR-357]] §3): só um
 * valor efetivamente medido autoriza a afirmação. `loading` e `unknown` calam.
 */
export type MeasuredCount =
  | { readonly state: "loading" }
  | { readonly state: "ok"; readonly count: number }
  | { readonly state: "unknown" };

/** Ainda medindo — não afirma, e não é falha. */
export const MEASURING: MeasuredCount = { state: "loading" };

/** A medição não chegou (rede, 5xx, auth). Nunca colapse isto para zero. */
export const UNMEASURED: MeasuredCount = { state: "unknown" };

export function measured(count: number): MeasuredCount {
  return { state: "ok", count };
}

/** Quantos sinais RENDERIZAR. Não-medido não vira linha — e quem afirma
 *  ausência consulta `allMeasured`, nunca este zero. */
export function signalCount(value: MeasuredCount): number {
  return value.state === "ok" ? value.count : 0;
}

/** Todos os contadores chegaram? Único predicado que autoriza afirmar ausência. */
export function allMeasured(...values: readonly MeasuredCount[]): boolean {
  return values.every((value) => value.state === "ok");
}
