export interface IrpfPeriodMatch {
  anoBase: number | null;
  defasadoAnos: number | null;
  authoritative: boolean;
}

const AUTHORITATIVE_MAX_GAP = 1;

export function derivePrimaryYear(
  labels: readonly string[] | undefined,
): number | null {
  if (!labels || labels.length === 0) return null;
  const last = labels[labels.length - 1];
  if (typeof last !== "string" || last.length < 4) return null;
  const year = Number.parseInt(last.slice(0, 4), 10);
  return Number.isFinite(year) ? year : null;
}

export function matchIrpfToPeriod(
  anosDisponiveis: readonly number[],
  primaryYear: number,
): IrpfPeriodMatch {
  const elegiveis = anosDisponiveis.filter((ano) => ano <= primaryYear + 1);
  if (elegiveis.length === 0) {
    return { anoBase: null, defasadoAnos: null, authoritative: false };
  }
  const anoBase = Math.max(...elegiveis);
  const defasadoAnos = primaryYear - anoBase;
  return {
    anoBase,
    defasadoAnos,
    authoritative: defasadoAnos <= AUTHORITATIVE_MAX_GAP,
  };
}
