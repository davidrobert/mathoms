import type { DashboardChart } from "@/lib/api";

/** Chart palette — fonte única em `design-tokens/tokens.json` (ADR-076). */
export const CHART_COLORS = Array.from({ length: 12 }, (_, i) => `var(--chart-${i + 1})`);

export function freshnessVariant(iso: string | null): "success" | "warning" {
  if (!iso) return "warning";
  const diff = Date.now() - new Date(iso).getTime();
  return diff > 30 * 24 * 60 * 60 * 1000 ? "warning" : "success";
}

export function formatFreshness(iso: string | null): string {
  if (!iso) return "Sem dados";
  const d = new Date(iso);
  return `Atualizado em ${d.toLocaleDateString("pt-BR")}`;
}

export interface BarDataRow {
  month: string;
  [key: string]: string | number;
}

export interface BarKey {
  key: string;
  name: string;
  color: string;
}

export function normalizeBarData(chart: DashboardChart): {
  rows: BarDataRow[];
  keys: BarKey[];
} {
  const raw = chart.data as {
    labels?: string[];
    datasets?: { label: string; data: number[] }[];
  };
  const labels = raw.labels ?? [];
  const datasets = raw.datasets ?? [];

  const rows: BarDataRow[] = labels.map((label, i) => {
    const row: BarDataRow = { month: label };
    datasets.forEach((ds) => {
      row[ds.label] = ds.data[i] ?? 0;
    });
    return row;
  });

  const keys = datasets.map((ds, i) => ({
    key: ds.label,
    name: ds.label,
    color: CHART_COLORS[i % CHART_COLORS.length],
  }));

  return { rows, keys };
}

export interface PieDataItem {
  name: string;
  value: number;
}

export function normalizePieData(chart: DashboardChart): PieDataItem[] {
  const raw = chart.data as Record<string, unknown>;

  if (Array.isArray(raw.labels) && Array.isArray(raw.values)) {
    const labels = raw.labels as string[];
    const values = raw.values as number[];
    return labels.map((label, i) => ({
      name: label,
      value: values[i] ?? 0,
    }));
  }

  return Object.entries(raw)
    .filter(([, v]) => typeof v === "number")
    .map(([name, value]) => ({ name, value: value as number }));
}

const PT_MONTHS: Record<string, string> = {
  jan: "01", fev: "02", mar: "03", abr: "04",
  mai: "05", jun: "06", jul: "07", ago: "08",
  set: "09", out: "10", nov: "11", dez: "12",
};

/** Converte label pt-BR "jan/2026" para range `{date_from, date_to}`.
 *  Retorna null se não reconhecer. Usado por deep-link do bar chart
 *  para `/transactions?date_from=...&date_to=...`. */
export function monthLabelToDateRange(
  label: string,
): { date_from: string; date_to: string } | null {
  const match = label.toLowerCase().match(/^([a-zç]+)\/?(\d{4})$/);
  if (!match) return null;
  const mm = PT_MONTHS[match[1]];
  const yyyy = match[2];
  if (!mm || !yyyy) return null;

  const start = `${yyyy}-${mm}-01`;
  const lastDay = new Date(Number(yyyy), Number(mm), 0).getDate();
  const end = `${yyyy}-${mm}-${String(lastDay).padStart(2, "0")}`;
  return { date_from: start, date_to: end };
}
