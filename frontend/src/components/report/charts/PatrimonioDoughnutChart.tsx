"use client";

import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
} from "recharts";
import { ReportCard } from "../ReportCard";
import type { PatrimonioData } from "@/types/report-analysis";

const CHART_COLORS = Array.from(
  { length: 12 },
  (_, i) => `var(--chart-${i + 1})`,
);

function fmtBRL(n: number): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(n);
}

/** F9 · F2.A · S1 — Chart "Composição Patrimonial" (PieChart).
 *
 * Substitui o canvas Chart.js `chart-patrimonio-doughnut` no template E6.
 * SVG nativo via Recharts, pronto para print e dark mode via tokens.
 */
export function PatrimonioDoughnutChart({
  patrimonio,
}: {
  patrimonio: PatrimonioData | undefined;
}) {
  const rows =
    patrimonio?.composicao ?? patrimonio?.tabela_categorias ?? [];
  const data = rows
    .filter((r) => r.valor > 0)
    .map((r) => ({ name: r.categoria, value: r.valor }));

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
    <ReportCard variant="neutral" title="Composição Patrimonial">
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              innerRadius={55}
              outerRadius={95}
              paddingAngle={2}
              stroke="var(--surface-card)"
              strokeWidth={2}
            >
              {data.map((_, idx) => (
                <Cell
                  key={idx}
                  fill={CHART_COLORS[idx % CHART_COLORS.length]}
                />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: "var(--surface-card)",
                border: "1px solid var(--surface-border)",
                borderRadius: "var(--radius-md)",
                color: "var(--surface-foreground)",
                fontFamily: "var(--font-body)",
                fontSize: "0.875rem",
              }}
              formatter={(value) => fmtBRL(Number(value))}
            />
            <Legend
              verticalAlign="bottom"
              iconType="circle"
              wrapperStyle={{
                fontFamily: "var(--font-body)",
                fontSize: "0.75rem",
                color: "var(--surface-muted-foreground)",
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </ReportCard>
  );
}
