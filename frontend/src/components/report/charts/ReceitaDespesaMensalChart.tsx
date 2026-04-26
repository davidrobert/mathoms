"use client";

import { useCallback, useMemo, useState } from "react";
import type {
  Chart as ChartJS,
  ChartData,
  ChartOptions,
  TooltipCallbacks,
} from "chart.js";

import { ReportCard } from "../ReportCard";
import { ChartCanvas } from "./primitives/ChartCanvas";
import { RDMLegend, type RDMLegendItem } from "./RDMLegend";
import { fmtBRL, pickColorByIndex } from "./_shared";
import { useIsPrint } from "../hooks/useIsPrint";
import type { ChartSeries, FluxoCaixaSummary } from "@/types/report-analysis";

const WINDOW = 12;

interface EnrichedDataset {
  readonly label: string;
  readonly data: readonly number[];
  readonly stack: "receita" | "despesa";
  readonly backgroundColor: string;
}

/** v2.E.6 — Chart "Receita vs Despesa — Mês a Mês" (Chart.js stacked).
 *
 * Substitui o AreaChart Recharts anterior; replica
 * `EXEMPLO_DE_RELATORIO.html:1794-1806` + script :7756-7939:
 *
 *  - Bar empilhado com 2 stack ids ("receita", "despesa").
 *  - Slide window de 12 meses com prev/next + dots.
 *  - Tooltip custom: title com sufixo do stack hovered, body listando
 *    apenas entries do mesmo stack ordenadas desc, footer com total.
 *  - Legenda agrupada custom (RDMLegend) com toggle clicavel.
 *  - chart-context (acima) e chart-conclusion (abaixo) auto-gerados.
 *  - Print mode: oculta nav/dots/legenda, fixa ultima janela 12m,
 *    renderiza bloco textual com totais consolidados de toda a serie.
 */
export function ReceitaDespesaMensalChart({
  fluxo,
}: {
  fluxo: FluxoCaixaSummary | undefined;
}) {
  const isPrint = useIsPrint();
  const det = fluxo?.receita_despesa_mensal_detalhado;
  const allLabels = det?.labels ?? [];
  const totalMonths = allLabels.length;
  const enriched = useEnrichedDatasets(det?.receita_datasets, det?.despesa_datasets);

  const [offset, setOffset] = useState<number>(() => Math.max(0, totalMonths - WINDOW));
  const [hiddenIdx, setHiddenIdx] = useState<ReadonlySet<number>>(() => new Set());
  const [chartInstance, setChartInstance] = useState<ChartJS | null>(null);

  const effectiveOffset = isPrint ? Math.max(0, totalMonths - WINDOW) : offset;
  const windowed = useMemo(
    () => sliceWindow(allLabels, enriched, effectiveOffset, WINDOW),
    [allLabels, enriched, effectiveOffset],
  );

  const onToggle = useCallback(
    (datasetIndex: number) => {
      setHiddenIdx((prev) => {
        const next = new Set(prev);
        if (next.has(datasetIndex)) next.delete(datasetIndex);
        else next.add(datasetIndex);
        return next;
      });
      if (chartInstance) {
        const meta = chartInstance.getDatasetMeta(datasetIndex);
        meta.hidden = !meta.hidden;
        chartInstance.update();
      }
    },
    [chartInstance],
  );

  const data = useMemo<ChartData<"bar">>(
    () => ({
      labels: [...windowed.labels],
      datasets: windowed.datasets.map((d) => ({
        label: d.label,
        data: [...d.data],
        backgroundColor: d.backgroundColor,
        stack: d.stack,
        borderRadius: 4,
        borderSkipped: false,
      })),
    }),
    [windowed],
  );

  const options = useMemo<ChartOptions<"bar">>(() => buildOptions(), []);

  if (!totalMonths || enriched.length === 0) return null;

  const maxOffset = Math.max(0, totalMonths - WINDOW);
  const totalPages = maxOffset + 1;
  const showNav = !isPrint && totalMonths > WINDOW;

  const periodLabel = formatPeriodLabel(windowed.labels);
  const context = buildContext(enriched, totalMonths);
  const conclusion = buildConclusion(enriched);
  const legend = buildLegendItems(enriched, hiddenIdx);

  return (
    <ReportCard variant="neutral" title="Receita vs Despesa — Mês a Mês">
      <p style={CONTEXT_STYLE} data-chart-context>
        {context}
      </p>

      {showNav && (
        <RDMNav
          page={effectiveOffset}
          total={totalPages}
          label={periodLabel}
          onPrev={() => setOffset((o) => Math.max(0, o - 1))}
          onNext={() => setOffset((o) => Math.min(maxOffset, o + 1))}
        />
      )}

      <div className="w-full">
        <ChartCanvas
          type="bar"
          data={data}
          options={options}
          height={256}
          ariaLabel="Receita vs Despesa Mês a Mês"
          onChartReady={setChartInstance}
        />
      </div>

      {!isPrint && (
        <RDMLegend
          receitas={legend.receitas}
          despesas={legend.despesas}
          onToggle={onToggle}
        />
      )}

      {isPrint && <PrintTotalsBlock enriched={enriched} />}

      <p style={CONCLUSION_STYLE} data-chart-conclusion>
        {conclusion}
      </p>
    </ReportCard>
  );
}

function useEnrichedDatasets(
  receita: readonly ChartSeries[] | undefined,
  despesa: readonly ChartSeries[] | undefined,
): readonly EnrichedDataset[] {
  return useMemo(() => {
    const out: EnrichedDataset[] = [];
    let colorIdx = 0;
    (receita ?? []).forEach((ds) => {
      out.push({
        label: ds.label,
        data: ds.data,
        stack: "receita",
        backgroundColor: ds.backgroundColor ?? pickColorByIndex(colorIdx++),
      });
    });
    (despesa ?? []).forEach((ds) => {
      out.push({
        label: ds.label,
        data: ds.data,
        stack: "despesa",
        backgroundColor: ds.backgroundColor ?? pickColorByIndex(colorIdx++),
      });
    });
    return out;
  }, [receita, despesa]);
}

interface SlicedWindow {
  readonly labels: readonly string[];
  readonly datasets: readonly EnrichedDataset[];
}

function sliceWindow(
  allLabels: readonly string[],
  datasets: readonly EnrichedDataset[],
  offset: number,
  size: number,
): SlicedWindow {
  const end = Math.min(offset + size, allLabels.length);
  const labels = allLabels.slice(offset, end);
  const sliced = datasets.map((d) => ({
    label: d.label,
    data: d.data.slice(offset, end),
    stack: d.stack,
    backgroundColor: d.backgroundColor,
  }));
  return { labels, datasets: sliced };
}

function buildOptions(): ChartOptions<"bar"> {
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "nearest", intersect: true },
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: tooltipCallbacks() },
      datalabels: { display: false },
    },
    scales: {
      x: { stacked: true, grid: { display: false } },
      y: {
        stacked: true,
        ticks: {
          callback: (v) => {
            const n = Number(v);
            if (Math.abs(n) >= 1000) return `R$ ${(n / 1000).toFixed(0)}k`;
            return `R$ ${Math.round(n)}`;
          },
        },
      },
    },
  };
}

/** Tooltip helpers portados de EXEMPLO_DE_RELATORIO.html:7798-7829.
 *
 * Exportados como funcoes puras (estruturais) para teste isolado em vitest:
 * o spec mocka `chart` + `tooltipItems` e checa string out, sem precisar
 * montar Chart.js completo (jsdom nao tem `canvas`). A funcao
 * `tooltipCallbacks()` adapta para a assinatura nominal do Chart.js. */
export interface RDMTooltipDataset {
  readonly label?: string;
  readonly stack?: string;
  readonly data: ReadonlyArray<number | null | undefined>;
}

export interface RDMTooltipItem {
  readonly dataset: RDMTooltipDataset;
  readonly dataIndex: number;
  readonly label?: string;
  readonly chart: { readonly data: { readonly datasets: ReadonlyArray<RDMTooltipDataset> } };
}

export function rdmTooltipTitle(items: readonly RDMTooltipItem[]): string {
  if (!items.length) return "";
  const stack = items[0].dataset.stack;
  const lbl = items[0].label ?? "";
  return `${lbl}${stack === "receita" ? " — Receitas" : " — Despesas"}`;
}

export function rdmTooltipBody(items: readonly RDMTooltipItem[]): readonly string[] {
  if (!items.length) return [];
  const hovered = items[0].dataset.stack;
  const idx = items[0].dataIndex;
  const entries: { label: string; value: number }[] = [];
  items[0].chart.data.datasets.forEach((ds) => {
    if (ds.stack === hovered && (ds.data[idx] ?? 0) > 0) {
      entries.push({ label: ds.label ?? "", value: ds.data[idx] ?? 0 });
    }
  });
  entries.sort((a, b) => b.value - a.value);
  return entries.map((e) => `${e.label}: ${fmtBRL(e.value)}`);
}

export function rdmTooltipFooter(items: readonly RDMTooltipItem[]): string {
  if (!items.length) return "";
  const hovered = items[0].dataset.stack;
  const idx = items[0].dataIndex;
  let total = 0;
  items[0].chart.data.datasets.forEach((ds) => {
    if (ds.stack === hovered) total += ds.data[idx] ?? 0;
  });
  return `Total: ${fmtBRL(total)}`;
}

function tooltipCallbacks(): Partial<TooltipCallbacks<"bar">> {
  return {
    title: (items) => rdmTooltipTitle(items as unknown as readonly RDMTooltipItem[]),
    beforeBody: (items) => [
      ...rdmTooltipBody(items as unknown as readonly RDMTooltipItem[]),
    ],
    label: () => "",
    footer: (items) => rdmTooltipFooter(items as unknown as readonly RDMTooltipItem[]),
  };
}

function buildLegendItems(
  enriched: readonly EnrichedDataset[],
  hidden: ReadonlySet<number>,
): { receitas: readonly RDMLegendItem[]; despesas: readonly RDMLegendItem[] } {
  const receitas: RDMLegendItem[] = [];
  const despesas: RDMLegendItem[] = [];
  enriched.forEach((d, i) => {
    const item: RDMLegendItem = {
      index: i,
      label: d.label,
      color: d.backgroundColor,
      hidden: hidden.has(i),
    };
    if (d.stack === "receita") receitas.push(item);
    else despesas.push(item);
  });
  return { receitas, despesas };
}

function buildContext(enriched: readonly EnrichedDataset[], totalMonths: number): string {
  const totalReceita = sumStack(enriched, "receita");
  const totalDespesa = sumStack(enriched, "despesa");
  const liquido = totalReceita - totalDespesa;
  return `Série temporal mensal (${totalMonths} ${totalMonths === 1 ? "mês" : "meses"}) de receitas (${fmtBRL(totalReceita)}) versus despesas (${fmtBRL(totalDespesa)}), com fluxo líquido de ${fmtBRL(liquido)}.`;
}

function buildConclusion(enriched: readonly EnrichedDataset[]): string {
  const totalReceita = sumStack(enriched, "receita");
  const totalDespesa = sumStack(enriched, "despesa");
  const months = enriched[0]?.data.length ?? 0;
  if (months === 0) return "";
  const mediaReceita = totalReceita / months;
  const mediaDespesa = totalDespesa / months;
  const taxaPoupanca = mediaReceita > 0 ? ((mediaReceita - mediaDespesa) / mediaReceita) * 100 : 0;
  return `Receita média de ${fmtBRL(mediaReceita)}/mês e despesa média de ${fmtBRL(mediaDespesa)}/mês. Taxa de poupança de ${taxaPoupanca.toFixed(1)}%.`;
}

function sumStack(enriched: readonly EnrichedDataset[], stack: "receita" | "despesa"): number {
  return enriched
    .filter((d) => d.stack === stack)
    .reduce((acc, d) => acc + d.data.reduce((sum, v) => sum + (v ?? 0), 0), 0);
}

function formatPeriodLabel(labels: readonly string[]): string {
  if (labels.length === 0) return "";
  if (labels.length === 1) return labels[0];
  return `${labels[0]}  —  ${labels[labels.length - 1]}`;
}

function PrintTotalsBlock({ enriched }: { readonly enriched: readonly EnrichedDataset[] }) {
  const totalReceita = sumStack(enriched, "receita");
  const totalDespesa = sumStack(enriched, "despesa");
  const liquido = totalReceita - totalDespesa;
  return (
    <div style={PRINT_BLOCK_STYLE} data-rdm-print-totals>
      <div>
        <strong>Total receitas:</strong> {fmtBRL(totalReceita)}
      </div>
      <div>
        <strong>Total despesas:</strong> {fmtBRL(totalDespesa)}
      </div>
      <div>
        <strong>Fluxo líquido:</strong> {fmtBRL(liquido)}
      </div>
    </div>
  );
}

interface RDMNavProps {
  readonly page: number;
  readonly total: number;
  readonly label: string;
  readonly onPrev: () => void;
  readonly onNext: () => void;
}

function RDMNav({ page, total, label, onPrev, onNext }: RDMNavProps) {
  return (
    <div data-rdm-nav style={NAV_WRAPPER_STYLE}>
      <div style={NAV_ROW_STYLE}>
        <button
          type="button"
          onClick={onPrev}
          disabled={page <= 0}
          aria-label="Meses anteriores"
          style={NAV_BTN_STYLE}
        >
          ‹
        </button>
        <span style={NAV_LABEL_STYLE} data-rdm-period>
          {label}
        </span>
        <button
          type="button"
          onClick={onNext}
          disabled={page >= total - 1}
          aria-label="Meses seguintes"
          style={NAV_BTN_STYLE}
        >
          ›
        </button>
      </div>
      <div style={DOTS_STYLE} aria-hidden="true" data-rdm-dots>
        {Array.from({ length: total }, (_, i) => (
          <span key={i} style={i === page ? DOT_ACTIVE_STYLE : DOT_STYLE} />
        ))}
      </div>
    </div>
  );
}

const CONTEXT_STYLE = {
  fontSize: 13,
  lineHeight: 1.5,
  color: "var(--surface-muted-foreground)",
  marginBottom: 12,
} as const;

const CONCLUSION_STYLE = {
  fontSize: 12,
  lineHeight: 1.5,
  marginTop: 12,
  padding: "10px 12px",
  borderLeft: "3px solid var(--brand-info)",
  background: "color-mix(in srgb, var(--brand-info) 6%, var(--surface-card))",
  borderRadius: "var(--radius-md)",
  color: "var(--surface-foreground)",
} as const;

const NAV_WRAPPER_STYLE = {
  marginBottom: 8,
} as const;

const NAV_ROW_STYLE = {
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  gap: 12,
  userSelect: "none",
} as const;

const NAV_BTN_STYLE = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  width: 28,
  height: 28,
  borderRadius: "50%",
  border: "1.5px solid var(--surface-border)",
  background: "var(--surface-background)",
  color: "var(--surface-foreground)",
  cursor: "pointer",
  fontSize: 16,
  fontWeight: 700,
} as const;

const NAV_LABEL_STYLE = {
  fontSize: 12,
  fontWeight: 600,
  color: "var(--surface-foreground)",
  minWidth: 160,
  textAlign: "center" as const,
};

const DOTS_STYLE = {
  display: "flex",
  gap: 5,
  justifyContent: "center",
  marginTop: 6,
} as const;

const DOT_STYLE = {
  width: 6,
  height: 6,
  borderRadius: "50%",
  background: "var(--surface-border)",
} as const;

const DOT_ACTIVE_STYLE = {
  ...DOT_STYLE,
  background: "var(--brand-accent)",
} as const;

const PRINT_BLOCK_STYLE = {
  display: "flex",
  flexDirection: "column" as const,
  gap: 4,
  marginTop: 10,
  padding: "8px 12px",
  borderRadius: "var(--radius-md)",
  background: "var(--surface-muted)",
  fontSize: 12,
};
