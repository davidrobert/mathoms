"use client";

import { useMemo, useState } from "react";

import { ReportCard } from "../ReportCard";
import { useIsPrint } from "../hooks/useIsPrint";
import { usePeriodWindow } from "../hooks/usePeriodWindow";
import { ChartBar } from "./primitives/ChartBar";
import type { ChartSeries as ChartPrimitiveSeries } from "./primitives/types";
import { PeriodToggle } from "../ui/PeriodToggle";
import type { Period } from "../ui/PeriodToggle";
import { fmtBRL, pickColorByIndex } from "./_shared";
import type { ChartSeries, FluxoCaixaSummary } from "@/types/report-analysis";

interface FonteAggregated {
  readonly label: string;
  readonly total: number;
  readonly color: string;
}

const PRINT_PERIOD: Period = "12m";
const TOP_N_CONTEXT = 3;

/** v2.E.4 · S2 — Chart "Receita por Fonte" em Chart.js com PeriodToggle.
 *
 * Migrado de Recharts → ChartBar (primitives) em v2.E.4. Consome
 * `receita_datasets[]` (séries mensais por fonte) em vez de `por_fonte`
 * agregado: o toggle 3M/6M/12M/Ano slica `data[start..end]` para recalcular
 * totais e re-ordenar fontes desc.
 *
 * Cores são atribuídas client-side por `pickColorByIndex` (paleta
 * `--chart-1..12`) — backend hoje só emite `{label, data}`. Mesma fonte
 * preserva mesma cor entre renders pois ordenação é determinística por
 * total desc.
 *
 * Print mode (`@media print`): oculta toggle e fixa em 12m.
 */
export function ReceitaBarChart({
  fluxo,
  conclusion,
}: {
  readonly fluxo: FluxoCaixaSummary | undefined;
  readonly conclusion?: string;
}) {
  const [periodState, setPeriod] = useState<Period>("12m");
  const isPrint = useIsPrint();
  const period = isPrint ? PRINT_PERIOD : periodState;

  const detalhado = fluxo?.receita_despesa_mensal_detalhado;
  const labels = useMemo(() => detalhado?.labels ?? [], [detalhado?.labels]);
  const datasets = useMemo(() => detalhado?.receita_datasets ?? [], [detalhado?.receita_datasets]);
  const window = usePeriodWindow(labels, period);

  const aggregated = useMemo(
    () => aggregateByFonte(datasets, window.start, window.end),
    [datasets, window.start, window.end],
  );

  if (aggregated.length === 0) return null;

  const total = aggregated.reduce((acc, f) => acc + f.total, 0);
  const chartSeries: readonly ChartPrimitiveSeries[] = aggregated.map((f) => ({
    label: f.label,
    data: [f.total],
    color: f.color,
  }));

  const chartContext = buildChartContext(aggregated, total);
  const fallbackConclusion = buildFallbackConclusion(aggregated, total);

  return (
    <ReportCard
      variant="neutral"
      title="Receita por Fonte"
      conclusion={conclusion ?? fallbackConclusion}
      headerRight={
        isPrint ? null : (
          <PeriodToggle value={period} onChange={setPeriod} periodLabel={window.label} />
        )
      }
    >
      <p
        className="mb-3 text-xs leading-relaxed text-[var(--surface-muted-foreground)]"
        data-chart-context
      >
        {chartContext}
      </p>
      <div className="w-full">
        <ChartBar
          labels={[""]}
          series={chartSeries}
          horizontal
          height={Math.max(160, aggregated.length * 32)}
          formatValue={fmtBRL}
          ariaLabel="Receita por Fonte"
        />
      </div>
    </ReportCard>
  );
}

function aggregateByFonte(
  datasets: readonly ChartSeries[],
  start: number,
  end: number,
): readonly FonteAggregated[] {
  const totals = datasets.map((ds, i) => ({
    label: humanizeLabel(ds.label),
    total: sumWindow(ds.data, start, end),
    originalIndex: i,
  }));
  const filtered = totals.filter((t) => t.total > 0);
  filtered.sort((a, b) => b.total - a.total);
  return filtered.map((t, idx) => ({
    label: t.label,
    total: t.total,
    color: pickColorByIndex(idx),
  }));
}

function sumWindow(data: readonly number[], start: number, end: number): number {
  if (end <= start) return 0;
  let sum = 0;
  for (let i = start; i < end && i < data.length; i++) {
    sum += Number.isFinite(data[i]) ? data[i] : 0;
  }
  return sum;
}

function humanizeLabel(raw: string): string {
  return raw.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function buildChartContext(
  aggregated: readonly FonteAggregated[],
  total: number,
): string {
  if (total <= 0) return "Sem receita registrada na janela selecionada.";
  const top = aggregated.slice(0, TOP_N_CONTEXT);
  const topShare = top.reduce((acc, f) => acc + f.total, 0);
  const restShare = Math.max(0, total - topShare);
  const restPct = ((restShare / total) * 100).toFixed(0);
  const topFmt = top.map((f) => `${f.label} (${((f.total / total) * 100).toFixed(0)}%)`).join(", ");
  if (aggregated.length <= TOP_N_CONTEXT) {
    return `Composição da receita total de ${fmtBRL(total)} por fonte: ${topFmt}.`;
  }
  return `Composição da receita total de ${fmtBRL(total)} por fonte: ${topFmt}, outras (${restPct}%).`;
}

function buildFallbackConclusion(
  aggregated: readonly FonteAggregated[],
  total: number,
): string | undefined {
  if (aggregated.length === 0 || total <= 0) return undefined;
  const top = aggregated[0];
  const topPct = ((top.total / total) * 100).toFixed(0);
  if (aggregated.length === 1) {
    return `Fonte única: ${top.label} (${fmtBRL(top.total)}). Considere diversificar para reduzir risco.`;
  }
  return `${top.label} lidera com ${fmtBRL(top.total)} (${topPct}%). Diversificação entre ${aggregated.length} fontes reduz risco de dependência única.`;
}
