"use client";

import { ReportSection } from "../ReportSection";
import { InvestimentosClasseCard } from "../cards/InvestimentosClasseCard";
import { EstrategiaAporteCard } from "../cards/EstrategiaAporteCard";
import { NarrativeChartCard } from "../charts/NarrativeChartCard";
import type { ReportAnalysisData } from "@/lib/api";

const CHART_TITLES: Record<string, string> = {
  alocacao_atual: "Alocação Atual",
  alocacao_alvo: "Alocação Alvo",
  top15_ativos: "Top 15 Ativos Financeiros",
  mariana_cenarios: "Cenários IF — Cônjuge",
};

/** F9 · F2.C — Seção S3 (Investimentos). */
export function S3InvestimentosSection({ data }: { data: ReportAnalysisData }) {
  const inv = data.investimentos as Record<string, unknown> | undefined;
  const goals = data.goals as Record<string, unknown> | undefined;
  const cenarios = data.cenarios_mariana as { aportes?: number[]; labels?: string[] } | undefined;
  const charts = (data.narrativas as Record<string, unknown> | undefined)?.charts as Record<string, unknown> | undefined;
  const ratios = data.ratios as Record<string, unknown> | undefined;

  return (
    <ReportSection id="S3" title="Investimentos — Carteira Financeira">
      {Object.keys(CHART_TITLES).map((cid) => (
        <NarrativeChartCard key={cid} chartId={cid} title={CHART_TITLES[cid]} narratives={charts} />
      ))}
      <div className="md:col-span-2">
        <InvestimentosClasseCard investimentos={inv as any} />
      </div>
      <div className="md:col-span-2">
        <EstrategiaAporteCard goals={goals} cenarios={cenarios} />
      </div>
      {ratios && (
        <div className="md:col-span-2 rounded-[var(--radius-card)] border border-[var(--surface-border)] bg-[var(--surface-card)] p-6">
          <h3 className="mb-2 font-display text-lg font-semibold">Rentabilidade</h3>
          <p className="font-mono text-2xl tabular-nums">
            {typeof (ratios as any).rentabilidade_pct === "number"
              ? `${((ratios as any).rentabilidade_pct as number).toFixed(2)}%`
              : String((ratios as any).rentabilidade_pct ?? "N/D")}
          </p>
        </div>
      )}
    </ReportSection>
  );
}
