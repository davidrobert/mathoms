"use client";

import { useMemo, useState } from "react";

import { ReportCard } from "../ReportCard";
import { ChartBar, useChartTheme } from "./primitives";
import type { ChartSeries } from "./primitives/types";
import { useIsPrint } from "../hooks/useIsPrint";
import { usePeriodWindow } from "../hooks/usePeriodWindow";
import { PeriodToggle, type Period } from "../ui/PeriodToggle";
import { fmtBRL, formatChartMonthLabel } from "./_shared";
import { pluralMeses } from "../utils/janelaLabel";
import type { FluxoCaixaSummary } from "@/types/report-analysis";

/** v2.E.3 — Chart "Fluxo de Caixa Mensal" em Chart.js (paridade
 * `EXEMPLO_DE_RELATORIO.html:1773-1779`).
 *
 * Stacked: receitas acima do zero (`--semantic-gain`) + saídas negativas
 * abaixo (`--semantic-neutral-financial`). `PeriodToggle` (3M/6M/12M/Ano) acima
 * do chart, `usePeriodWindow` aplica o slice. Em `@media print` o toggle
 * fica oculto e o período é fixado em 12m.
 *
 * `totais_despesa` é BRUTO: inclui o aporte, que é poupança e não consumo
 * (ADR-333). Daí "Saídas (inclui aportes)", o nome do `/plano`, e a cor neutra:
 * "Despesa" nomearia, na mesma S2, a base da rosca que tira o aporte, e o
 * vermelho leria a poupança como perda.
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
  const receitas = (det?.totais_receita ?? []).slice(window.start, window.end);
  const saidas = (det?.totais_despesa ?? []).slice(window.start, window.end);

  const series: ChartSeries[] = [
    { label: "Receitas", data: receitas, color: theme.semantic.gain },
    {
      label: "Saídas (inclui aportes)",
      data: saidas.map((v) => -v),
      color: theme.semantic.neutral,
    },
  ];

  const context = buildContext(slicedLabels);

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
        formatTooltipValue={(v) => fmtBRL(Math.abs(v))}
        ariaLabel="Fluxo de caixa mensal: receitas acima do zero; saídas, aportes incluídos, abaixo."
        height={256}
      />
    </ReportCard>
  );
}

/** Descreve só o que está DESENHADO: contagem e range vêm do mesmo lugar, as
 * barras renderizadas. Misturar contagem do payload com range do render
 * produzia "últimos 8 meses (jan/25 a dez/25)" com 12 barras (I3).
 *
 * O agregado rotulado (ADR-306 D1) vive só na conclusão do card
 * (`conclusionUtils.buildFluxoMensal`): repeti-lo aqui imprimia os mesmos dois
 * números duas vezes, e o qualificador "aportes incluídos" junto. */
function buildContext(slicedLabels: readonly string[]): string | null {
  const n = slicedLabels.length;
  if (n === 0) return null;
  const first = slicedLabels[0];
  const last = slicedLabels[n - 1];
  const range = first === last ? first : `${first} a ${last}`;
  return `No gráfico: ${n} ${pluralMeses(n)} (${range}).`;
}
