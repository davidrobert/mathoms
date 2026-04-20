"use client";

import { ReportSection } from "../ReportSection";
import { SectionSummary } from "../SectionSummary";
import { InvestimentosClasseCard } from "../cards/InvestimentosClasseCard";
import { EstrategiaAporteCard } from "../cards/EstrategiaAporteCard";
import { ContrafluxoCard } from "../cards/ContrafluxoCard";
import { NarrativeChartCard } from "../charts/NarrativeChartCard";
import type { ReportAnalysisData } from "@/lib/api";

/** F9 · F2.C — Seção S3 (Investimentos). */
export function S3InvestimentosSection({ data }: { data: ReportAnalysisData }) {
  const inv = data.investimentos as Record<string, unknown> | undefined;
  const goals = data.goals as Record<string, unknown> | undefined;
  const cenarios = data.cenarios_mariana as { aportes?: number[]; labels?: string[] } | undefined;
  const narrativas = data.narrativas as Record<string, unknown> | undefined;
  const charts = narrativas?.charts as Record<string, unknown> | undefined;
  const ratios = data.ratios as Record<string, unknown> | undefined;

  // estrategia_aporte lives inside investimentos (report_spec §9)
  const estrategiaAporte = inv?.estrategia_aporte as Record<string, unknown> | undefined;

  return (
    <ReportSection id="S3" title="Investimentos — Carteira Financeira">
      <SectionSummary narrativas={narrativas} sectionId="S3" />

      {/* Alocação Atual e Alvo — side-by-side (half each) */}
      <NarrativeChartCard
        chartId="alocacao_atual"
        title="Alocação Atual"
        narratives={charts}
        size="half"
      />
      <NarrativeChartCard
        chartId="alocacao_alvo"
        title="Alocação Alvo"
        narratives={charts}
        size="half"
      />

      {/* Demais charts — full width */}
      <NarrativeChartCard chartId="top15_ativos" title="Top 15 Ativos Financeiros" narratives={charts} />
      <NarrativeChartCard chartId="mariana_cenarios" title="Cenários IF — Cônjuge" narratives={charts} />

      <div className="md:col-span-2">
        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
        <InvestimentosClasseCard investimentos={inv as any} />
      </div>
      <div className="md:col-span-2">
        <EstrategiaAporteCard
          estrategia={estrategiaAporte as any}
          goals={goals}
          cenarios={cenarios}
        />
      </div>
      <div className="md:col-span-2">
        <ContrafluxoCard
          contrafluxo={inv?.contrafluxo as any}
          cdi_anual={inv?.cdi_anual as number | undefined}
        />
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
