"use client";

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ReportCard } from "../ReportCard";
import { CHART_COLORS, fmtBRL, fmtCompact, TOOLTIP_STYLE, AXIS_TICK, LABEL_TICK } from "./_shared";
import type { FluxoCaixaSummary } from "@/types/report-analysis";

/** F9 · F2.B · S2 — Chart "Receita por Fonte" (BarChart horizontal). */
export function ReceitaBarChart({
  fluxo,
}: {
  fluxo: FluxoCaixaSummary | undefined;
}) {
  const rows = fluxo?.tabela_receitas ?? [];
  const data = rows
    .filter((r) => r.valor > 0)
    .map((r) => ({ name: r.categoria, value: r.valor }));

  if (data.length === 0) return null;

  return (
    <ReportCard variant="neutral" title="Receita por Fonte">
      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
          >
            <XAxis type="number" tickFormatter={fmtCompact} tick={AXIS_TICK} tickLine={false} axisLine={false} />
            <YAxis
              dataKey="name"
              type="category"
              width={130}
              tick={LABEL_TICK}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(value) => fmtBRL(Number(value))} />
            <Bar dataKey="value" radius={[0, 6, 6, 0]}>
              {data.map((_, idx) => (
                <Cell key={idx} fill={CHART_COLORS[idx % CHART_COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </ReportCard>
  );
}
