"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ReportCard } from "../ReportCard";
import { fmtBRL, fmtCompact, TOOLTIP_STYLE, AXIS_TICK, LABEL_TICK } from "./_shared";
import type { FluxoCaixaSummary } from "@/types/report-analysis";

/** F9 · F2.B · S2 — Chart "Receita vs Despesa — Mês a Mês" (AreaChart). */
export function ReceitaDespesaMensalChart({
  fluxo,
}: {
  fluxo: FluxoCaixaSummary | undefined;
}) {
  const det = fluxo?.receita_despesa_mensal_detalhado;
  if (!det?.labels?.length) return null;

  const data = det.labels.map((label, i) => ({
    month: label,
    receita: det.totais_receita?.[i] ?? 0,
    despesa: det.totais_despesa?.[i] ?? 0,
  }));

  return (
    <ReportCard variant="neutral" title="Receita vs Despesa — Mês a Mês">
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--surface-border)" />
            <XAxis dataKey="month" tick={LABEL_TICK} tickLine={false} />
            <YAxis tickFormatter={fmtCompact} tick={AXIS_TICK} tickLine={false} axisLine={false} />
            <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(value) => fmtBRL(Number(value))} />
            <Area
              type="monotone"
              dataKey="receita"
              stroke="var(--semantic-gain)"
              fill="var(--semantic-gain)"
              fillOpacity={0.15}
              name="Receita"
            />
            <Area
              type="monotone"
              dataKey="despesa"
              stroke="var(--semantic-loss)"
              fill="var(--semantic-loss)"
              fillOpacity={0.15}
              name="Despesa"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </ReportCard>
  );
}
