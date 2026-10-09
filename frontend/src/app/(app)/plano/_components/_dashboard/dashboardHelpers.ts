import type { DashboardChart } from "@/lib/api";
import { MONTH_SHORT_PT_LOWER } from "@/lib/monthLabel";

/** Chart palette — fonte única em `design-tokens/tokens.json` (ADR-076). */
export const CHART_COLORS = Array.from({ length: 12 }, (_, i) => `var(--chart-${i + 1})`);

/** Papel que o payload declara por série. Sem ele a série cai na paleta categórica
 *  — e `--chart-2` tem o hex de `--semantic-gain`: a 2ª série sairia verde. */
const TONE_COLORS: Record<string, string> = {
  gain: "var(--semantic-gain)",
  neutral: "var(--semantic-neutral-financial)",
  loss: "var(--semantic-loss)",
};

/** Recharts pinta o texto da legenda com a cor da série (`labelStyle.color || entry.color`)
 *  — `--chart-4` sobre o card dá 2,06:1 — e o ordena alfabeticamente por default. Texto
 *  neutro, cor só no ícone, e a ordem do payload: fatia maior primeiro, receitas antes. */
export const LEGEND_PROPS = {
  labelStyle: { color: "var(--muted-foreground)" },
  itemSorter: null,
} as const;

/** Mais que isso não cabe em meia largura: os rótulos do eixo começam a sumir. */
const MAX_MESES_MEIA_LARGURA = 6;

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

interface BarDataset {
  label: string;
  data: number[];
  tone?: string;
}

function seriesColor(dataset: BarDataset, index: number): string {
  const byTone = dataset.tone ? TONE_COLORS[dataset.tone] : undefined;
  return byTone ?? CHART_COLORS[index % CHART_COLORS.length];
}

export function normalizeBarData(chart: DashboardChart): {
  rows: BarDataRow[];
  keys: BarKey[];
} {
  const raw = chart.data as { labels?: string[]; datasets?: BarDataset[] };
  const labels = raw.labels ?? [];
  const datasets = raw.datasets ?? [];

  const rows: BarDataRow[] = labels.map((label, i) => {
    const row: BarDataRow = { month: label };
    datasets.forEach((ds) => {
      row[ds.label] = ds.data[i] ?? 0;
    });
    return row;
  });

  const keys = datasets.map((ds, i) => ({ key: ds.label, name: ds.label, color: seriesColor(ds, i) }));

  return { rows, keys };
}

const ISO_MONTH = /^(\d{4})-(\d{2})$/;

/** "2026-02" → `{date_from: "2026-02-01", date_to: "2026-02-28"}` para o deep-link de
 *  `/transactions`; `null` para rótulo que não é mês ISO. */
export function isoMonthToDateRange(
  label: string,
): { date_from: string; date_to: string } | null {
  const match = ISO_MONTH.exec(label);
  if (!match) return null;
  const [, yyyy, mm] = match;
  const month = Number(mm);
  if (month < 1 || month > 12) return null;
  const lastDay = new Date(Number(yyyy), month, 0).getDate();
  return { date_from: `${yyyy}-${mm}-01`, date_to: `${yyyy}-${mm}-${String(lastDay).padStart(2, "0")}` };
}

/** "2026-02" → "fev/26" (COPY §5: eixo de gráfico em `MMM/YY`); fora do formato, cru. */
export function formatIsoMonthShort(label: string): string {
  const match = ISO_MONTH.exec(label);
  const month = match ? Number(match[2]) : 0;
  if (!match || month < 1 || month > 12) return label;
  return `${MONTH_SHORT_PT_LOWER[month - 1]}/${match[1].slice(2)}`;
}

// Barra deitada: 36px por categoria (rótulo de 2 linhas não encosta no vizinho) sobre 34px
// fixos (eixo de valores + margem do topo); o piso alinha com a altura dos outros cards.
const CATEGORY_ROW_PX = 36;
const CATEGORY_CHROME_PX = 34;
const CHART_MIN_HEIGHT_PX = 300;

export function categoryBarChartHeight(categories: number): number {
  return Math.max(CHART_MIN_HEIGHT_PX, CATEGORY_CHROME_PX + CATEGORY_ROW_PX * categories);
}

/** Eixo de meses é o que o payload declara (`x_axis: "month"`), nunca o título nem o
 *  formato do rótulo: colunas com deep-link por mês. Qualquer outro eixo (classes de
 *  investimento) é de categorias — barra deitada e sem clique, que não teria destino. */
export function isMonthlyBarChart(chart: DashboardChart): boolean {
  return (chart.data as { x_axis?: unknown }).x_axis === "month";
}

export function isWideChart(chart: DashboardChart): boolean {
  if (chart.chart_type !== "bar" || !isMonthlyBarChart(chart)) return false;
  return normalizeBarData(chart).rows.length > MAX_MESES_MEIA_LARGURA;
}
