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
import { useChartTheme, type ChartPalette } from "./primitives/useChartTheme";
import { RDMLegend, type RDMLegendItem } from "./RDMLegend";
import { fmtBRL, formatChartMonthLabel } from "./_shared";
import { useIsPrint } from "../hooks/useIsPrint";
import { formatBRLAxisTick } from "@/lib/format";
import type { ChartSeries, FluxoCaixaSummary } from "@/types/report-analysis";
import {
  CONCLUSION_STYLE,
  CONTEXT_STYLE,
  DOTS_STYLE,
  DOT_ACTIVE_STYLE,
  DOT_STYLE,
  NAV_BTN_STYLE,
  NAV_LABEL_STYLE,
  NAV_ROW_STYLE,
  NAV_WRAPPER_STYLE,
  PRINT_BLOCK_STYLE,
} from "./rdmStyles";

const WINDOW = 12;

interface EnrichedDataset {
  readonly label: string;
  readonly data: readonly number[];
  readonly stack: "receita" | "despesa";
  readonly backgroundColor: string;
}

/** v2.E.6 — Chart "Receitas e Saídas por Categoria — Mês a Mês" (Chart.js
 * stacked).
 *
 * A pilha de `despesa_datasets` se chama "Saídas" porque inclui o aporte, que é
 * poupança e não consumo (ADR-333): "Despesas" nomearia, na mesma S2, a base da
 * rosca que tira o aporte. O aporte fica na pilha — a visibilidade da poupança
 * pertence às superfícies de fluxo (ADR-333 §Emenda). "Por Categoria" separa
 * este card do "Receitas e Saídas por Mês" do `/plano`, que é o de totais.
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
  const theme = useChartTheme();
  const palette = useMemo(() => paletaSemSemantica(theme), [theme]);
  const det = fluxo?.receita_despesa_mensal_detalhado;
  const allLabels = det?.labels ?? [];
  const totalMonths = allLabels.length;
  const enriched = useEnrichedDatasets(
    det?.receita_datasets,
    det?.despesa_datasets,
    palette,
  );

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
  const conclusion = buildConclusion(enriched, totalMonths);
  const legend = buildLegendItems(enriched, hiddenIdx);

  return (
    <ReportCard variant="neutral" title="Receitas e Saídas por Categoria — Mês a Mês">
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
          ariaLabel="Receitas e saídas por categoria, mês a mês; aportes incluídos nas saídas"
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

      {conclusion && (
        <p style={CONCLUSION_STYLE} data-chart-conclusion>
          {conclusion}
        </p>
      )}
    </ReportCard>
  );
}

function enrichSeriesForStack(
  series: readonly ChartSeries[] | undefined,
  stack: "receita" | "despesa",
  startIdx: number,
  palette: readonly string[],
): { datasets: EnrichedDataset[]; nextIdx: number } {
  const datasets: EnrichedDataset[] = [];
  let idx = startIdx;
  const len = Math.max(palette.length, 1);
  (series ?? []).forEach((ds) => {
    // palette vem de `paletaSemSemantica(useChartTheme())`: as 12 entradas
    // categóricas (LIGHT_FALLBACK garante) menos as semânticas. `palette[0]`
    // cobre o caso degenerado (palette vazia em SSR/teste sem CSS) sem hex
    // literal.
    const fallback = palette[((idx % len) + len) % len] ?? palette[0];
    datasets.push({
      label: ds.label,
      data: ds.data,
      stack,
      backgroundColor: ds.backgroundColor ?? fallback,
    });
    idx++;
  });
  return { datasets, nextIdx: idx };
}

/** `--chart-2/3` repetem `--semantic-gain/loss`. Na ordem do produtor (receitas,
 * depois saídas em ordem alfabética), o aporte cai num desses slots com uma ou
 * duas fontes de receita e sairia verde ou vermelho — ganho ou perda, o que a
 * ADR-333 nega. A paleta da RDM pula toda cor semântica. */
function paletaSemSemantica(theme: ChartPalette): readonly string[] {
  const semanticas = new Set(
    [theme.semantic.gain, theme.semantic.loss].map((c) => c.toLowerCase()),
  );
  const livres = theme.categorical.filter((c) => !semanticas.has(c.toLowerCase()));
  return livres.length > 0 ? livres : theme.categorical;
}

function useEnrichedDatasets(
  receita: readonly ChartSeries[] | undefined,
  despesa: readonly ChartSeries[] | undefined,
  palette: readonly string[],
): readonly EnrichedDataset[] {
  return useMemo(() => {
    const r = enrichSeriesForStack(receita, "receita", 0, palette);
    const d = enrichSeriesForStack(despesa, "despesa", r.nextIdx, palette);
    return [...r.datasets, ...d.datasets];
  }, [receita, despesa, palette]);
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
  const labels = allLabels.slice(offset, end).map(formatChartMonthLabel);
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
        beginAtZero: true,
        ticks: {
          callback: (v, _i, ticks) =>
            formatBRLAxisTick(Number(v), ticks.map((t) => t.value)),
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
  return `${lbl}${stack === "receita" ? " — Receitas" : " — Saídas"}`;
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

/** Escopo dos totais citados — os dois textos somam a série INTEIRA
 * (`enriched`), não a página renderizada pelo `RDMNav`. */
function mesesDocumentados(n: number): string {
  return `${n} ${n === 1 ? "mês documentado" : "meses documentados"}`;
}

/** Cláusula só para a pilha que existe: sem `despesa_datasets` o texto imprimia
 * "despesas (R$ 0)" — zero afirmado sobre dado ausente, e com a copy nova seria
 * "aportes incluídos" sobre ele. */
function buildContext(enriched: readonly EnrichedDataset[], totalMonths: number): string {
  const clausulas: string[] = [];
  if (hasStack(enriched, "receita")) {
    clausulas.push(`receitas (${fmtBRL(sumStack(enriched, "receita"))})`);
  }
  if (hasStack(enriched, "despesa")) {
    clausulas.push(`saídas (${fmtBRL(sumStack(enriched, "despesa"))}, aportes incluídos)`);
  }
  return `Série temporal mensal de ${clausulas.join(" versus ")} em ${mesesDocumentados(totalMonths)}.`;
}

/** Totaliza a janela renderizada — **sem mensalizar e sem taxa** (ADR-306 D1).
 *
 * Este texto emitia `R$ X/mês`, `R$ Y/mês` e `Taxa de poupança de Z%` derivados
 * da série inteira, todos sem rótulo: uma segunda mensalização e uma segunda
 * taxa de poupança, sob base diferente da canônica, no MESMO S2 que já publica
 * as duas (fluxo mensal na janela 12m; taxa no hero de S1). O leitor não tinha
 * como reconciliar 42.667/mês com 92.000/mês. A divisão da lane já declarava
 * esta forma em `conclusionUtils.ts` — só não estava implementada.
 *
 * "Após aportes" rotula a base: as saídas incluem o aporte, e quem poupa muito
 * veria um líquido perto de zero ao lado da taxa de poupança do hero. Sem uma
 * das pilhas não há líquido a afirmar. */
function buildConclusion(enriched: readonly EnrichedDataset[], totalMonths: number): string {
  if (totalMonths === 0 || !temAsDuasPilhas(enriched)) return "";
  const liquido = sumStack(enriched, "receita") - sumStack(enriched, "despesa");
  return `Fluxo líquido após aportes de ${fmtBRL(liquido)} em ${mesesDocumentados(totalMonths)}.`;
}

function hasStack(enriched: readonly EnrichedDataset[], stack: "receita" | "despesa"): boolean {
  return enriched.some((d) => d.stack === stack);
}

function temAsDuasPilhas(enriched: readonly EnrichedDataset[]): boolean {
  return hasStack(enriched, "receita") && hasStack(enriched, "despesa");
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

/** No PDF a legenda some, então o qualificador do aporte vai no rótulo impresso. */
function PrintTotalsBlock({ enriched }: { readonly enriched: readonly EnrichedDataset[] }) {
  const totalReceita = sumStack(enriched, "receita");
  const totalSaidas = sumStack(enriched, "despesa");
  return (
    <div style={PRINT_BLOCK_STYLE} data-rdm-print-totals>
      {hasStack(enriched, "receita") && (
        <div>
          <strong>Total receitas:</strong> {fmtBRL(totalReceita)}
        </div>
      )}
      {hasStack(enriched, "despesa") && (
        <div>
          <strong>Total saídas (aportes incluídos):</strong> {fmtBRL(totalSaidas)}
        </div>
      )}
      {temAsDuasPilhas(enriched) && (
        <div>
          <strong>Fluxo líquido após aportes:</strong> {fmtBRL(totalReceita - totalSaidas)}
        </div>
      )}
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
