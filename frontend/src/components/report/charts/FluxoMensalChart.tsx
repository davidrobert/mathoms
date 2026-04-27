"use client";

import { useMemo, useState } from "react";

import { ReportCard } from "../ReportCard";
import { ChartBar, useChartTheme } from "./primitives";
import type { ChartSeries } from "./primitives/types";
import { useIsPrint } from "../hooks/useIsPrint";
import { usePeriodWindow } from "../hooks/usePeriodWindow";
import { PeriodToggle, type Period } from "../ui/PeriodToggle";
import { fmtBRL } from "./_shared";
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

  const slicedLabels = labels.slice(window.start, window.end);
  const receita = (det?.totais_receita ?? []).slice(window.start, window.end);
  const despesa = (det?.totais_despesa ?? []).slice(window.start, window.end);

  const series: ChartSeries[] = [
    { label: "Receita", data: receita, color: theme.semantic.gain },
    { label: "Despesa", data: despesa.map((v) => -v), color: theme.semantic.loss },
  ];

  const context = buildContext(slicedLabels, fluxo);
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
): string | null {
  if (slicedLabels.length === 0) return null;
  const receita = fluxo?.receita_recorrente_mensal;
  const despesa = fluxo?.despesa_mensal_media;
  if (typeof receita !== "number" || typeof despesa !== "number") return null;
  const first = slicedLabels[0];
  const last = slicedLabels[slicedLabels.length - 1];
  const range = first === last ? first : `${first} a ${last}`;
  return `Janela dos últimos ${slicedLabels.length} meses (${range}). Receita recorrente média de ${fmtBRL(receita)}/mês versus despesa média de ${fmtBRL(despesa)}/mês.`;
}

function buildFallbackConclusion(fluxo: FluxoCaixaSummary | undefined): string | undefined {
  const receita = fluxo?.receita_recorrente_mensal;
  const despesa = fluxo?.despesa_mensal_media;
  if (typeof receita !== "number" || typeof despesa !== "number") return undefined;
  const liquido = receita - despesa;
  const taxa = receita > 0 ? (liquido / receita) * 100 : 0;
  return `Saldo recorrente mensal de ${fmtBRL(liquido)}/mês. Taxa de poupança recorrente de ${taxa.toFixed(1).replace(".", ",")}%.`;
}
