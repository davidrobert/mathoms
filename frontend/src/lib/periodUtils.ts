export type Period = "3m" | "6m" | "12m" | "ytd";

export const PERIOD_LABELS: Record<Period, string> = {
  "3m": "3M",
  "6m": "6M",
  "12m": "12M",
  ytd: "YTD",
};

const PT_BR_MONTHS: Record<string, number> = {
  jan: 1,
  fev: 2,
  mar: 3,
  abr: 4,
  mai: 5,
  jun: 6,
  jul: 7,
  ago: 8,
  set: 9,
  out: 10,
  nov: 11,
  dez: 12,
};

/** Converte um label mensal do chart no último dia local daquele mês. */
export function parseChartMonthLabel(label: string): Date | null {
  const trimmed = label.trim().toLowerCase();
  const numeric = /^(\d{2})\/(\d{2})$/.exec(trimmed);
  if (numeric) {
    const yy = Number(numeric[1]);
    const mm = Number(numeric[2]);
    if (mm >= 1 && mm <= 12) return new Date(2000 + yy, mm, 0);
    return null;
  }
  const named = /^([a-zç]{3})\/(\d{2})$/.exec(trimmed);
  if (!named) return null;
  const month = PT_BR_MONTHS[named[1]];
  return month ? new Date(2000 + Number(named[2]), month, 0) : null;
}

function parseIsoDate(value: string | undefined): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec((value ?? "").trim());
  if (!match) return null;
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
}

/** Resolve a âncora realizada usada pelos charts e pelo card de pontuais. */
export function resolveAnchorDate(
  labels: string[] | undefined,
  dataCorte: string | undefined,
): Date | undefined {
  const last = labels?.length
    ? parseChartMonthLabel(labels[labels.length - 1])
    : null;
  const corte = parseIsoDate(dataCorte);
  if (!corte) return last ?? undefined;
  return last && last < corte ? last : corte;
}
