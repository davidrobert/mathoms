/** Shared chart utilities and styles for Recharts components (F9 · F2). */

export const CHART_COLORS = Array.from(
  { length: 12 },
  (_, i) => `var(--chart-${i + 1})`,
);

/** v2.E — Atribui cor estável da paleta categórica via índice (módulo 12).
 *
 * Backend (`fluxo_caixa_enricher`) emite `ChartSeries` com apenas
 * `{label, data}` — frontend é responsável pela atribuição de cor.
 * Stable: mesmo índice → mesma cor em qualquer render.
 *
 * @deprecated Retorna literal "var(--chart-N)" — Chart.js não resolve CSS
 * vars no canvas (renderiza preto). Para charts Chart.js, use
 * `useChartTheme().categorical[idx % len]` que resolve via
 * getComputedStyle. Mantido por compat com `PatrimonioDoughnutChart`
 * (Recharts, que resolve CSS vars no DOM). */
export function pickColorByIndex(idx: number): string {
  const len = CHART_COLORS.length;
  const safe = ((idx % len) + len) % len;
  return CHART_COLORS[safe];
}

const MONTH_SHORT_PT_LOWER = [
  "jan", "fev", "mar", "abr", "mai", "jun",
  "jul", "ago", "set", "out", "nov", "dez",
] as const;

/** Backend `analyze_finances.py:1311` emite labels de chart mensais no formato
 * `"yy/mm"` (ex.: `"26/02"`). Esse formato confunde — facilmente lido como
 * `dd/MM`. Helper converte para pt-BR `"MMM/aa"` (ex.: `"fev/26"`).
 *
 * Falha graciosamente: retorna o input cru se o formato não casar
 * `^\d{2}/\d{2}$` ou se o mês estiver fora de 01-12. */
export function formatChartMonthLabel(label: string): string {
  const m = /^(\d{2})\/(\d{2})$/.exec(label);
  if (!m) return label;
  const year = m[1];
  const month = parseInt(m[2], 10);
  if (isNaN(month) || month < 1 || month > 12) return label;
  return `${MONTH_SHORT_PT_LOWER[month - 1]}/${year}`;
}

export function fmtBRL(n: number): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(n);
}

export function fmtCompact(n: number): string {
  return new Intl.NumberFormat("pt-BR", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(n);
}

export const TOOLTIP_STYLE = {
  background: "var(--surface-card)",
  border: "1px solid var(--surface-border)",
  borderRadius: "var(--radius-md)",
  color: "var(--surface-foreground)",
  fontFamily: "var(--font-body)",
  fontSize: "0.875rem",
} as const;

export const AXIS_TICK = {
  fontFamily: "var(--font-mono)",
  fontSize: 11,
  fill: "var(--surface-muted-foreground)",
} as const;

export const LABEL_TICK = {
  fontFamily: "var(--font-body)",
  fontSize: 12,
  fill: "var(--surface-muted-foreground)",
} as const;
