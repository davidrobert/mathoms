"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ReferenceLine,
} from "recharts";
import { ReportCard } from "../ReportCard";
import { fmtBRL, fmtCompact, TOOLTIP_STYLE, AXIS_TICK, LABEL_TICK } from "./_shared";
import type { FluxoCaixaSummary } from "@/types/report-analysis";

/** F9 · F2.B · S2 — Chart "Fluxo de Caixa Mensal" (receita - despesa stacked).
 *
 * Mostra barra positiva (receita) e negativa (despesa) empilhadas
 * por mês com linha de referência no zero.
 */
export function FluxoMensalChart({
  fluxo,
}: {
  fluxo: FluxoCaixaSummary | undefined;
}) {
  const det = fluxo?.receita_despesa_mensal_detalhado;
  if (!det?.labels?.length) return null;

  const data = det.labels.map((label, i) => {
    const receita = det.totais_receita?.[i] ?? 0;
    const despesa = det.totais_despesa?.[i] ?? 0;
    return {
      month: label,
      receita,
      despesa: -despesa,
      fluxo: receita - despesa,
    };
  });

  return (
    <ReportCard variant="neutral" title="Fluxo de Caixa Mensal">
      <div className="w-full">
        <ResponsiveContainer width="100%" height={256}>
          <BarChart data={data} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--surface-border)" />
            <XAxis dataKey="month" tick={LABEL_TICK} tickLine={false} />
            <YAxis tickFormatter={fmtCompact} tick={AXIS_TICK} tickLine={false} axisLine={false} />
            <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(value) => fmtBRL(Math.abs(Number(value)))} />
            <ReferenceLine y={0} stroke="var(--surface-muted-foreground)" strokeDasharray="3 3" />
            <Bar dataKey="receita" fill="var(--semantic-gain)" fillOpacity={0.8} name="Receita" radius={[4, 4, 0, 0]} />
            <Bar dataKey="despesa" fill="var(--semantic-loss)" fillOpacity={0.8} name="Despesa" radius={[0, 0, 4, 4]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </ReportCard>
  );
}
