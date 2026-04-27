"use client";

import { ReportSection } from "../ReportSection";
import { SectionSnapshotDiff } from "../SectionSnapshotDiff";
import { SectionSummary } from "../SectionSummary";
import {
  ContrafluxoCard,
  EstrategiaAporteCard,
  InvestimentosClasseCard,
  type ContrafluxoData,
  type EstrategiaAporteData,
  type InvestimentosClasseData,
} from "../cards";
import { NarrativeChartCard } from "../charts/NarrativeChartCard";
import { deriveChartConclusion } from "../utils/conclusionUtils";
import type { ReportAnalysisData } from "@/lib/api";

interface InvestimentosBlock extends InvestimentosClasseData {
  estrategia_aporte?: EstrategiaAporteData;
  contrafluxo?: ContrafluxoData;
  cdi_anual?: number;
}

interface Ratios {
  rentabilidade_pct?: number | string;
  [key: string]: unknown;
}

/** F9 · F2.C — Seção S3 (Investimentos). */
export function S3InvestimentosSection({ data }: { data: ReportAnalysisData }) {
  const inv = data.investimentos as unknown as InvestimentosBlock | undefined;
  const goals = data.goals as Record<string, unknown> | undefined;
  const cenarios = data.cenarios_mariana as { aportes?: number[]; labels?: string[] } | undefined;
  const narrativas = data.narrativas as Record<string, unknown> | undefined;
  const charts = narrativas?.charts as Record<string, unknown> | undefined;
  const ratios = data.ratios as unknown as Ratios | undefined;

  const estrategiaAporte = inv?.estrategia_aporte;
  const rentabilidade = ratios?.rentabilidade_pct;

  return (
    <ReportSection id="S3" title="Investimentos — Carteira Financeira">
      <SectionSummary narrativas={narrativas} sectionId="S3" />

      {/* Alocação Atual e Alvo — side-by-side (half each) */}
      <NarrativeChartCard
        chartId="alocacao_atual"
        title="Alocação Atual"
        narratives={charts}
        size="half"
        fallbackConclusion={deriveChartConclusion("alocacao_atual", data)}
      />
      <NarrativeChartCard
        chartId="alocacao_alvo"
        title="Alocação Alvo"
        narratives={charts}
        size="half"
        fallbackConclusion={deriveChartConclusion("alocacao_alvo", data)}
      />

      {/* Demais charts — full width */}
      <NarrativeChartCard
        chartId="top15_ativos"
        title="Top 15 Ativos Financeiros"
        narratives={charts}
        fallbackConclusion={deriveChartConclusion("top15_ativos", data)}
      />
      <NarrativeChartCard
        chartId="mariana_cenarios"
        title="Cenários IF — Cônjuge"
        narratives={charts}
        fallbackConclusion={deriveChartConclusion("mariana_cenarios", data)}
      />

      <div className="md:col-span-2">
        <InvestimentosClasseCard investimentos={inv} />
      </div>
      <div className="md:col-span-2">
        <EstrategiaAporteCard
          estrategia={estrategiaAporte}
          goals={goals}
          cenarios={cenarios}
        />
      </div>
      <div className="md:col-span-2">
        <ContrafluxoCard
          contrafluxo={inv?.contrafluxo}
          cdi_anual={inv?.cdi_anual}
        />
      </div>
      {ratios && (
        <div className="md:col-span-2 rounded-[var(--radius-card)] border border-[var(--surface-border)] bg-[var(--surface-card)] p-6">
          <h3 className="mb-2 font-display text-lg font-semibold">Rentabilidade</h3>
          <p className="font-mono text-2xl tabular-nums">
            {typeof rentabilidade === "number"
              ? `${rentabilidade.toFixed(2)}%`
              : String(rentabilidade ?? "N/D")}
          </p>
        </div>
      )}

      {/* v2.8 (ADR-148) — comparisons + changelog vs relatório anterior. */}
      <SectionSnapshotDiff sectionId="S3" data={data} />
    </ReportSection>
  );
}
