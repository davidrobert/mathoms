// Formas curtas de BRL para rótulo (COPY_GUIDELINES §4.2). Fora de `format.ts`
// pelo mesmo motivo de `monthLabel.ts`: aquele arquivo está no teto de 500
// linhas do gate T2. `format.ts` importa as instâncias e re-exporta os helpers,
// então o consumidor continua importando de `@/lib/format`.

export const BRL_NO_CENTS = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 0,
});

export const COMPACT_BRL = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  notation: "compact",
  maximumFractionDigits: 1,
});

// Sem opção de casas, o compact do Intl arredonda a 2 dígitos significativos e
// só escreve decimal abaixo de 10. É mais estreito que a casa fixa do §4.5
// (`R$ 123 mil`, não `R$ 123,5 mil`): o rótulo de dado disputa a largura com a
// fatia, e o valor cheio fica no tooltip.
const DATA_LABEL_BRL = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  notation: "compact",
});

/** Rótulo de dado de gráfico: "R$ 4,6 mil", "R$ 23 mil", "R$ 1,2 mi". */
export function formatBRLDataLabel(value: number): string {
  return DATA_LABEL_BRL.format(value);
}

/** Tick de eixo monetário: completo sem centavos ("R$ 20.000"); compact
 * ("R$ 1,5 mi") quando algum tick da escala chega a milhões. */
export function formatBRLAxisTick(value: number, escala: readonly number[]): string {
  const emMilhoes = escala.some((tick) => Math.abs(tick) >= 1_000_000);
  return (emMilhoes ? COMPACT_BRL : BRL_NO_CENTS).format(value);
}
