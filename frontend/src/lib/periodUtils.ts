import type { TransactionItem } from "@/lib/api";

export type Period = "3m" | "6m" | "12m" | "ytd";

export const PERIOD_LABELS: Record<Period, string> = {
  "3m": "3M",
  "6m": "6M",
  "12m": "12M",
  ytd: "YTD",
};

/** Retorna date_from e date_to (YYYY-MM-DD) para o período selecionado. */
export function getPeriodDates(period: Period): {
  date_from: string;
  date_to: string;
} {
  const today = new Date();
  const start = new Date(today);

  switch (period) {
    case "3m":
      start.setMonth(today.getMonth() - 3);
      break;
    case "6m":
      start.setMonth(today.getMonth() - 6);
      break;
    case "12m":
      start.setFullYear(today.getFullYear() - 1);
      break;
    case "ytd":
      start.setMonth(0, 1);
      break;
  }

  return {
    date_from: start.toISOString().split("T")[0],
    date_to: today.toISOString().split("T")[0],
  };
}

/** Número aproximado de meses no período (para calcular médias mensais). */
export function getPeriodMonths(period: Period): number {
  switch (period) {
    case "3m":
      return 3;
    case "6m":
      return 6;
    case "12m":
      return 12;
    case "ytd":
      return Math.max(1, new Date().getMonth() + 1);
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

