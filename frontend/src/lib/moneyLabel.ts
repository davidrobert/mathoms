// Formas curtas de BRL para rótulo (COPY_GUIDELINES §4.2). Fora de `format.ts`
// pelo mesmo motivo de `monthLabel.ts`: aquele arquivo está no teto de 500
// linhas do gate T2. `format.ts` importa as instâncias daqui, então o
// consumidor continua importando de `@/lib/format`.

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
