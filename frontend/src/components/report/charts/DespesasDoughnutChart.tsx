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
import { CHART_COLORS, fmtBRL, TOOLTIP_STYLE } from "./_shared";
import type { FluxoCaixaSummary } from "@/types/report-analysis";

const CATEGORY_LABELS: Record<string, string> = {
  assinaturas: "Assinaturas",
  seguros: "Seguros",
  financeiro: "Financeiro",
  impostos: "Impostos",
  nao_identificado: "Não identificado",
  reserva_desejos: "Reserva de desejos",
  transporte: "Transporte",
  financiamentos: "Financiamentos",
  moradia: "Moradia",
  alimentacao: "Alimentação",
  suporte_familiar: "Suporte familiar",
  saude: "Saúde",
  lazer_viagens: "Lazer e viagens",
  vestuario: "Vestuário",
  educacao: "Educação",
  servicos_domesticos: "Serviços domésticos",
  melhoria_reforma: "Melhoria e reforma",
};

/** F9 · F2.B · S2 — Chart "Despesas por Categoria" (PieChart). */
export function DespesasDoughnutChart({
  fluxo,
}: {
  fluxo: FluxoCaixaSummary | undefined;
}) {
  const raw = fluxo?.despesas_por_categoria ?? {};
  const data = Object.entries(raw)
    .filter(([, v]) => v > 0)
    .map(([key, value]) => ({
      name: CATEGORY_LABELS[key] ?? key,
      value,
    }))
    .sort((a, b) => b.value - a.value);

  if (data.length === 0) return null;

  return (
    <ReportCard variant="neutral" title="Despesas por Categoria">
      <div className="w-full">
        <ResponsiveContainer width="100%" height={288}>
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
              {data.map((entry, idx) => (
                <Cell
                  key={`cell-${entry.name}-${idx}`}
                  fill={CHART_COLORS[idx % CHART_COLORS.length]}
                />
              ))}
            </Pie>
            <Tooltip
              contentStyle={TOOLTIP_STYLE}
              formatter={(value) => fmtBRL(Number(value))}
            />
            <Legend
              verticalAlign="bottom"
              iconType="circle"
              wrapperStyle={{
                fontFamily: "var(--font-body)",
                fontSize: "0.7rem",
                color: "var(--surface-muted-foreground)",
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </ReportCard>
  );
}
