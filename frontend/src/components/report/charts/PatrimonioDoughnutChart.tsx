"use client";

import { ReportCard } from "../ReportCard";
import { ChartDonut } from "./primitives/ChartDonut";
import { fmtBRL } from "./_shared";
import type { PatrimonioData } from "@/types/report-analysis";

/** W5-T02 (v2.E.9) · S1 — Chart "Composição Patrimonial" (Chart.js doughnut).
 *
 * Migrado de Recharts → `ChartDonut` (primitives), fechando o resíduo
 * intencional da Onda v2.E (ADR-139, emenda 2026-07-08). Paleta
 * categórica (`--chart-1..12`) resolvida pelo `useChartTheme` dentro do
 * primitive; legenda bottom + tooltip BRL preservam a versão Recharts.
 */
export function PatrimonioDoughnutChart({
  patrimonio,
  conclusion,
}: {
  patrimonio: PatrimonioData | undefined;
  conclusion?: string;
}) {
  const rows = patrimonio?.composicao ?? patrimonio?.tabela_categorias ?? [];
  const data = rows
    .filter((r) => r.valor > 0)
    .map((r) => ({ label: r.categoria, value: r.valor }));

  if (data.length === 0) {
    return (
      <ReportCard variant="neutral" title="Composição Patrimonial">
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Sem dados suficientes para o gráfico.
        </p>
      </ReportCard>
    );
  }

  return (
    <ReportCard variant="neutral" title="Composição Patrimonial" conclusion={conclusion}>
      <div className="w-full">
        <ChartDonut
          data={data}
          formatValue={fmtBRL}
          height={288}
          ariaLabel="Composição patrimonial por categoria"
        />
      </div>
    </ReportCard>
  );
}
