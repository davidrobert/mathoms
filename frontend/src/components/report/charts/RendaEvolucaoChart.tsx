"use client";

import { useMemo } from "react";
import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import { ChartLine, useChartTheme } from "./primitives";
import type { ChartSeries } from "./primitives/types";
import { fmtBRL } from "./_shared";
import { parseDecimalString, type IrpfKpis } from "@/types/irpf";

interface RendaEvolucaoChartProps {
  kpis: IrpfKpis;
  conclusion?: string;
}

interface YearPoint {
  year: number;
  value: number;
}

function buildSeries(kpis: IrpfKpis): YearPoint[] {
  const out: YearPoint[] = [];
  for (const [yearKey, valueStr] of Object.entries(kpis.evolucao_renda_anos)) {
    const year = Number(yearKey);
    const value = parseDecimalString(valueStr);
    if (Number.isInteger(year) && value !== null) {
      out.push({ year, value });
    }
  }
  out.sort((a, b) => a.year - b.year);
  return out;
}

function SinglePointFallback({ point, conclusion }: { point: YearPoint; conclusion?: string }) {
  return (
    <ReportCard variant="neutral" title="Evolução da Renda — Multi-anos" conclusion={conclusion}>
      <div className="space-y-2">
        <p className="text-xs uppercase tracking-wide text-[var(--surface-muted-foreground)]">
          Ano-base {point.year}
        </p>
        <MonetaryValue value={point.value} size="kpi" />
        <p className="text-xs leading-relaxed text-[var(--surface-muted-foreground)]">
          A comparação multi-anos aparece a partir de duas declarações processadas.
        </p>
      </div>
    </ReportCard>
  );
}

/** ADR-157 · S_IRPF_RENDA — evolução multi-anos da renda anual familiar. */
export function RendaEvolucaoChart({ kpis, conclusion }: RendaEvolucaoChartProps) {
  const theme = useChartTheme();
  const points = useMemo(() => buildSeries(kpis), [kpis]);

  if (points.length === 0) {
    return (
      <ReportCard variant="neutral" title="Evolução da Renda — Multi-anos">
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Sem dados de renda anual disponíveis.
        </p>
      </ReportCard>
    );
  }
  if (points.length === 1) {
    return <SinglePointFallback point={points[0]} conclusion={conclusion} />;
  }

  const labels = points.map((p) => String(p.year));
  const series: ChartSeries[] = [
    { label: "Renda Anual Familiar", data: points.map((p) => p.value), color: theme.primary },
  ];

  return (
    <ReportCard variant="neutral" title="Evolução da Renda — Multi-anos" conclusion={conclusion}>
      <ChartLine
        labels={labels}
        series={series}
        filled
        smooth={false}
        formatValue={(v) => fmtBRL(v)}
        ariaLabel={`Evolução da renda anual familiar entre ${labels[0]} e ${labels[labels.length - 1]}`}
        height={256}
      />
    </ReportCard>
  );
}
