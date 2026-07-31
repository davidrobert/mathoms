/** Shared chart utilities for the Chart.js charts in `/reports/**` (F9 · F2).
 *
 * Resíduo Recharts (CHART_COLORS/pickColorByIndex/TOOLTIP_STYLE/AXIS_TICK/
 * LABEL_TICK) removido em W5-T02 / v2.E.9 (ADR-139, emenda 2026-07-08) —
 * paleta categórica agora vem de `useChartTheme().categorical`, que resolve
 * `--chart-1..12` via getComputedStyle (Chart.js não resolve CSS vars no
 * canvas).
 */

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

/** A40.l3 — range da janela renderizada, legível em PROSA.
 *
 * `usePeriodWindow().label` devolve o range cru do payload ("25/01 — 25/12") e
 * serve bem como rótulo do `<PeriodToggle>`, ao lado dos botões. Em texto
 * corrido o mesmo formato se lê como dd/MM — e no PDF o toggle não renderiza,
 * então a prosa fica sendo o único portador da base. */
export function formatRangeHumano(rangeLabel: string): string {
  const partes = rangeLabel.split("—").map((p) => formatChartMonthLabel(p.trim()));
  return partes.length === 2 ? `${partes[0]} a ${partes[1]}` : partes.join("");
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
