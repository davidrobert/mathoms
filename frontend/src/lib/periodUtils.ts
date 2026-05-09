import type { TransactionItem } from "@/lib/api";

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

/** Aceita "YY/MM" (ex.: "26/04") ou "mes/aa" pt-BR (ex.: "abr/26") e retorna
 * o último dia do mês como Date. Mesmo formato consumido por
 * `usePeriodWindow` em charts (paridade de ancora chart ↔ card). */
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
  if (named) {
    const month = PT_BR_MONTHS[named[1]];
    if (!month) return null;
    return new Date(2000 + Number(named[2]), month, 0);
  }
  return null;
}

/** Retorna date_from e date_to (YYYY-MM-DD) para o período selecionado.
 * `anchorDate` ancora o `date_to` no fim da janela de dados (default: hoje). */
export function getPeriodDates(
  period: Period,
  anchorDate?: Date,
): {
  date_from: string;
  date_to: string;
} {
  const end = anchorDate ?? new Date();
  const start = new Date(end);

  switch (period) {
    case "3m":
      start.setMonth(end.getMonth() - 3);
      break;
    case "6m":
      start.setMonth(end.getMonth() - 6);
      break;
    case "12m":
      start.setFullYear(end.getFullYear() - 1);
      break;
    case "ytd":
      start.setFullYear(end.getFullYear(), 0, 1);
      break;
  }

  return {
    date_from: start.toISOString().split("T")[0],
    date_to: end.toISOString().split("T")[0],
  };
}

/** Número aproximado de meses no período (para calcular médias mensais).
 * `anchorDate` define o "ano/mês corrente" do YTD (default: hoje). */
export function getPeriodMonths(period: Period, anchorDate?: Date): number {
  switch (period) {
    case "3m":
      return 3;
    case "6m":
      return 6;
    case "12m":
      return 12;
    case "ytd": {
      const ref = anchorDate ?? new Date();
      return Math.max(1, ref.getMonth() + 1);
    }
  }
}

// Prefixos de categoria que indicam receita no pipeline Mathoms AI.
const INCOME_PREFIXES = ["receita_", "outras_receitas"];

export function isIncomeCategory(categoria: string): boolean {
  return INCOME_PREFIXES.some((p) => categoria.startsWith(p));
}

/**
 * Agrega receitas por categoria a partir de uma lista de transações.
 * Retorna Record<categoria, totalBRL>.
 */
export function aggregateReceitas(
  transactions: TransactionItem[],
): Record<string, number> {
  const result: Record<string, number> = {};
  for (const t of transactions) {
    if (!t.categoria) continue;
    if (isIncomeCategory(t.categoria) && t.valor > 0) {
      result[t.categoria] = (result[t.categoria] ?? 0) + t.valor;
    }
  }
  return result;
}

/**
 * Agrega despesas por categoria e retorna médias mensais.
 * Retorna Record<categoria, mediaMensalBRL>.
 */
export function aggregateDespesasMediaMensal(
  transactions: TransactionItem[],
  numMonths: number,
): Record<string, number> {
  const totals: Record<string, number> = {};
  for (const t of transactions) {
    if (!t.categoria) continue;
    if (!isIncomeCategory(t.categoria) && t.valor > 0) {
      totals[t.categoria] = (totals[t.categoria] ?? 0) + t.valor;
    }
  }
  const months = Math.max(1, numMonths);
  const result: Record<string, number> = {};
  for (const [cat, total] of Object.entries(totals)) {
    result[cat] = total / months;
  }
  return result;
}
