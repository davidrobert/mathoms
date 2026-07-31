"use client";

import { useMemo, useState } from "react";

import { ReportCard } from "../ReportCard";
import { ChartBar, useChartTheme } from "./primitives";
import type { ChartSeries } from "./primitives/types";
import { useIsPrint } from "../hooks/useIsPrint";
import { usePeriodWindow } from "../hooks/usePeriodWindow";
import { PeriodToggle, type Period } from "../ui/PeriodToggle";
import { fmtBRL, formatChartMonthLabel } from "./_shared";
import { resolveFluxoJanelaMensal, type FluxoJanelaMensal } from "../utils/fluxoJanela";
import { describeJanelaEscopo, pluralMeses } from "../utils/janelaLabel";
import type { FluxoCaixaSummary } from "@/types/report-analysis";

/** v2.E.3 — Chart "Fluxo de Caixa Mensal" em Chart.js (paridade
 * `EXEMPLO_DE_RELATORIO.html:1773-1779`).
 *
 * Stacked: receita acima do zero (`--semantic-gain`) + despesa negativa
 * abaixo (`--semantic-loss`). `PeriodToggle` (3M/6M/12M/Ano) acima do
 * chart, `usePeriodWindow` aplica o slice. Em `@media print` o toggle
 * fica oculto e o período é fixado em 12m.
 */
export function FluxoMensalChart({
  fluxo,
  conclusion,
}: {
  fluxo: FluxoCaixaSummary | undefined;
  conclusion?: string;
}) {
  const det = fluxo?.receita_despesa_mensal_detalhado;
  const labels = useMemo(() => det?.labels ?? [], [det?.labels]);
  const isPrint = useIsPrint();
  const theme = useChartTheme();
  const [period, setPeriod] = useState<Period>("12m");
  const effectivePeriod: Period = isPrint ? "12m" : period;
  const window = usePeriodWindow(labels, effectivePeriod);

  if (!labels.length) return null;

  const slicedLabels = labels.slice(window.start, window.end).map(formatChartMonthLabel);
  const receita = (det?.totais_receita ?? []).slice(window.start, window.end);
  const despesa = (det?.totais_despesa ?? []).slice(window.start, window.end);

  const series: ChartSeries[] = [
    { label: "Receita", data: receita, color: theme.semantic.gain },
    { label: "Despesa", data: despesa.map((v) => -v), color: theme.semantic.loss },
  ];

  const context = buildContext(slicedLabels, fluxo, effectivePeriod);

  return (
    <ReportCard variant="neutral" title="Fluxo de Caixa Mensal" conclusion={conclusion}>
      {context && (
        <p
          data-chart-context
          className="mb-3 text-xs leading-relaxed text-[var(--surface-muted-foreground)]"
        >
          {context}
        </p>
      )}
      {!isPrint && (
        <PeriodToggle value={period} onChange={setPeriod} periodLabel={window.label} />
      )}
      <ChartBar
        labels={slicedLabels}
        series={series}
        stacked
        formatValue={(v) => fmtBRL(v)}
        ariaLabel="Fluxo de caixa mensal — receita e despesa empilhadas"
        height={256}
      />
    </ReportCard>
  );
}

/** Duas cláusulas com origens distintas — misturá-las produzia "últimos 8
 * meses (jan/25 a dez/25)" com 12 barras (I3): a contagem vinha do payload e o
 * range do render. A primeira cláusula descreve o que está DESENHADO; a
 * segunda declara a base do agregado citado, sempre rotulada. */
function buildContext(
  slicedLabels: readonly string[],
  fluxo: FluxoCaixaSummary | undefined,
  effectivePeriod: Period,
): string | null {
  if (slicedLabels.length === 0) return null;
  const renderizada = describeRenderizada(slicedLabels);
  // 3M/6M/YTD não têm bloco agregado no payload, e derivar a média de
  // `totais_receita` trocaria receita recorrente por receita bruta
  // (fluxo_caixa_enricher.py:432,471). Omitir é o único caminho honesto.
  if (effectivePeriod !== "12m") return renderizada;
  const janela = resolveFluxoJanelaMensal(fluxo);
  if (!janela) return renderizada;
  return `${renderizada} ${describeAgregado(janela)}`;
}

/** Contagem e range vêm do MESMO lugar: as barras desenhadas. */
function describeRenderizada(slicedLabels: readonly string[]): string {
  const n = slicedLabels.length;
  const first = slicedLabels[0];
  const last = slicedLabels[n - 1];
  const range = first === last ? first : `${first} a ${last}`;
  return `No gráfico: ${n} ${pluralMeses(n)} (${range}).`;
}

/** ADR-306 D1 — agregado só aparece com rótulo explícito da própria base,
 * inclusive quando é 12m: o leitor não pode inferir a base pela posição. */
function describeAgregado(janela: FluxoJanelaMensal): string {
  const receita = `${fmtBRL(janela.receitaRecorrenteMensal)}/mês`;
  const despesa = `${fmtBRL(janela.despesaMensalMedia)}/mês`;
  return `Média sobre ${describeJanelaEscopo(janela.rotulo)}: receita recorrente de ${receita} versus despesa média de ${despesa}.`;
}
