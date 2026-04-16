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
import type { PatrimonioData } from "@/types/report-analysis";

interface WaterfallIfChartProps {
  patrimonio: PatrimonioData | undefined;
  goals:
    | {
        if_meta?: number;
        if_pct?: number;
        if_gap?: number;
      }
    | undefined;
}

function fmtCompact(n: number): string {
  return new Intl.NumberFormat("pt-BR", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(n);
}

function fmtFull(n: number): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(n);
}

/** F9 · F2.A · S1 — Chart "Caminho para a Independência Financeira".
 *
 * Substitui o canvas `chart-waterfall-if`. Mostra 3 barras:
 * atual (investível), gap até a meta, meta total.
 */
export function WaterfallIfChart({
  patrimonio,
  goals,
}: WaterfallIfChartProps) {
  const atual = patrimonio?.investivel ?? 0;
  const meta = goals?.if_meta ?? 0;
  const gap = goals?.if_gap ?? Math.max(0, meta - atual);
  const pct = goals?.if_pct ?? (meta > 0 ? (atual / meta) * 100 : 0);

  if (meta === 0) {
    return (
      <ReportCard variant="neutral" title="Caminho para Independência Financeira">
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Meta de IF não configurada.
        </p>
      </ReportCard>
    );
  }

  const data = [
    { name: "Atual", value: atual, color: "var(--brand-primary)" },
    { name: "Gap", value: gap, color: "var(--semantic-alert)" },
    { name: "Meta", value: meta, color: "var(--semantic-gain)" },
  ];

  return (
    <ReportCard variant="neutral" title="Caminho para Independência Financeira">
      <p className="mb-3 text-sm text-[var(--surface-muted-foreground)]">
        Progresso atual:{" "}
        <span className="font-mono font-semibold text-[var(--brand-primary)] tabular-nums">
          {pct.toFixed(1).replace(".", ",")}%
        </span>{" "}
        da meta.
      </p>
      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 20, right: 8, left: -12, bottom: 0 }}>
            <XAxis
              dataKey="name"
              tick={{
                fontFamily: "var(--font-body)",
                fontSize: 12,
                fill: "var(--surface-muted-foreground)",
              }}
              tickLine={false}
              axisLine={{ stroke: "var(--surface-border)" }}
            />
            <YAxis
              tickFormatter={fmtCompact}
              tick={{
                fontFamily: "var(--font-mono)",
                fontSize: 11,
                fill: "var(--surface-muted-foreground)",
              }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              contentStyle={{
                background: "var(--surface-card)",
                border: "1px solid var(--surface-border)",
                borderRadius: "var(--radius-md)",
                color: "var(--surface-foreground)",
                fontFamily: "var(--font-body)",
                fontSize: "0.875rem",
              }}
              formatter={(value) => fmtFull(Number(value))}
              cursor={{ fill: "var(--surface-muted)" }}
            />
            <Bar dataKey="value" radius={[6, 6, 0, 0]}>
              {data.map((entry, idx) => (
                <Cell key={idx} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </ReportCard>
  );
}
