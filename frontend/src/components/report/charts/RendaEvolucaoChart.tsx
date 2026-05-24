"use client";

import { useMemo } from "react";
import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import { ChartLine, useChartTheme } from "./primitives";
import type { ChartSeries } from "./primitives/types";
import { fmtBRL } from "./_shared";
import { type CompletudeAno, type IrpfKpis, parseDecimalString } from "@/types/irpf";

interface RendaEvolucaoChartProps {
  kpis: IrpfKpis;
  conclusion?: string;
}

interface YearPoint {
  year: number;
  value: number;
  completude: CompletudeAno;
}

function buildSeries(kpis: IrpfKpis): YearPoint[] {
  const completudeMap = kpis.anos_completude_por_ano ?? {};
  const out: YearPoint[] = [];
  for (const [yearKey, valueStr] of Object.entries(kpis.evolucao_renda_anos)) {
    const year = Number(yearKey);
    const value = parseDecimalString(valueStr);
    if (Number.isInteger(year) && value !== null) {
      out.push({ year, value, completude: completudeMap[yearKey] ?? "completo" });
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
        <p className="font-mono text-3xl font-semibold tabular-nums">
          <MonetaryValue value={point.value} />
        </p>
        <p className="text-xs leading-relaxed text-[var(--surface-muted-foreground)]">
          A comparação multi-anos aparece a partir de duas declarações processadas.
        </p>
      </div>
    </ReportCard>
  );
}

/** ADR-157 · ADR-266 · S_IRPF_RENDA — evolução multi-anos. Anos provisorio/incompleto marcados na legenda. */
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
      <CompletudeLegend points={points} />
    </ReportCard>
  );
}

function CompletudeLegend({ points }: { points: YearPoint[] }) {
  // Mostra apenas anos não-completos (ADR-266 transparência: chart entrega
  // detalhe, card opina). Quando todos completos, legenda fica oculta.
  const flagged = points.filter((p) => p.completude !== "completo");
  if (flagged.length === 0) return null;
  return (
    <ul className="mt-3 flex flex-wrap gap-2 text-xs" aria-label="Anos com completude diferenciada">
      {flagged.map((p) => (
        <CompletudeChip key={p.year} year={p.year} state={p.completude} />
      ))}
    </ul>
  );
}

function CompletudeChip({ year, state }: { year: number; state: CompletudeAno }) {
  const label = state === "provisorio" ? "provisório" : "incompleto";
  return (
    <li className="inline-flex items-center gap-1 rounded-full bg-[var(--report-alert-warning-bg)] px-2.5 py-0.5 font-medium text-[var(--report-alert-warning-text)]">
      <span aria-hidden="true">●</span>
      <span>
        {year} · {label}
      </span>
    </li>
  );
}
