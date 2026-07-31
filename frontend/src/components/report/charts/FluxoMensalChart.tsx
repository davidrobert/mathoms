"use client";

import { useMemo, useState } from "react";

import { ReportCard } from "../ReportCard";
import { ChartBar, useChartTheme } from "./primitives";
import type { ChartSeries } from "./primitives/types";
import { useIsPrint } from "../hooks/useIsPrint";
import { usePeriodWindow } from "../hooks/usePeriodWindow";
import { PeriodToggle, type Period } from "../ui/PeriodToggle";
import { fmtBRL, formatChartMonthLabel } from "./_shared";
import {
  describeJanelaEscopo,
  resolveFluxoJanelaMensal,
  type FluxoJanelaMensal,
} from "../utils/fluxoJanela";
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
  const fallbackConclusion = conclusion ?? buildFallbackConclusion(fluxo);

  return (
    <ReportCard variant="neutral" title="Fluxo de Caixa Mensal" conclusion={fallbackConclusion}>
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

function buildContext(
  slicedLabels: readonly string[],
  fluxo: FluxoCaixaSummary | undefined,
  effectivePeriod: Period,
): string | null {
  if (slicedLabels.length === 0) return null;
  const janela = resolveFluxoJanelaMensal(fluxo);
  if (!janela) return null;
  const first = slicedLabels[0];
  const last = slicedLabels[slicedLabels.length - 1];
  const range = first === last ? first : `${first} a ${last}`;
  // 3M/6M/YTD não têm bloco agregado no payload, e derivar a média de
  // `totais_receita` trocaria receita recorrente por receita bruta
  // (fluxo_caixa_enricher.py:432,471). Omitir é o único caminho honesto.
  if (effectivePeriod !== "12m") {
    return `Janela dos últimos ${slicedLabels.length} meses (${range}).`;
  }
  const meses = janela.janela === "12m" ? janela.janelaMeses : undefined;
  return `Janela dos últimos ${meses ?? slicedLabels.length} meses (${range}). ${describeAgregado(janela)}`;
}

/** ADR-306 D1 — agregado full só aparece com rótulo explícito de período. */
function describeAgregado(janela: FluxoJanelaMensal): string {
  const receita = `${fmtBRL(janela.receitaRecorrenteMensal)}/mês`;
  const despesa = `${fmtBRL(janela.despesaMensalMedia)}/mês`;
  if (janela.janela === "12m") {
    return `Receita recorrente média de ${receita} versus despesa média de ${despesa}.`;
  }
  return `Média sobre ${describeJanelaEscopo(janela)}: receita recorrente de ${receita} versus despesa média de ${despesa}.`;
}

function buildFallbackConclusion(fluxo: FluxoCaixaSummary | undefined): string | undefined {
  const janela = resolveFluxoJanelaMensal(fluxo);
  if (!janela) return undefined;
  const base = `Saldo recorrente mensal de ${fmtBRL(janela.sobraMensal)}/mês, medido sobre ${describeJanelaEscopo(janela)}.`;
  const taxa = janela.taxaPoupancaRecorrentePct;
  // Bloco `full` não emite taxa_poupanca_*; recomputar de despesa_mensal_media
  // reintroduziria o aporte no numerador (erro que ADR-333 fechou).
  if (taxa === undefined) return base;
  return `${base} Taxa de poupança recorrente de ${taxa.toFixed(1).replace(".", ",")}%.`;
}
