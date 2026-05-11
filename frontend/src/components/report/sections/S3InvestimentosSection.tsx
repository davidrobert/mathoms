"use client";

import { ReportSection } from "../ReportSection";
import { SectionSnapshotDiff } from "../SectionSnapshotDiff";
import { SectionSummary } from "../SectionSummary";
import {
  ContrafluxoCard,
  EstrategiaAporteCard,
  InvestimentosClasseCard,
  RentabilidadeCard,
  Top15AtivosCard,
  type ContrafluxoData,
  type EstrategiaAporteData,
  type InvestimentosClasseData,
  type Top15AtivosData,
} from "../cards";
import { NarrativeChartCard } from "../charts/NarrativeChartCard";
import { deriveChartConclusion } from "../utils/conclusionUtils";
import type { ReportAnalysisData } from "@/lib/api";
import type { RatiosData } from "@/types/report-analysis";

interface InvestimentosBlock extends InvestimentosClasseData, Top15AtivosData {
  estrategia_aporte?: EstrategiaAporteData;
  contrafluxo?: ContrafluxoData;
  cdi_anual?: number;
}

/** F9 · F2.C — Seção S3 (Investimentos). */
export function S3InvestimentosSection({ data }: { data: ReportAnalysisData }) {
  const inv = data.investimentos as unknown as InvestimentosBlock | undefined;
  const goals = data.goals as Record<string, unknown> | undefined;
  // ADR-166 (A8.4 PR3): fallback dual-key removido — chave universal estável.
  const cenarios = data.cenarios_conjuge as
    | { aportes?: number[]; labels?: string[] }
    | undefined;
  const narrativas = data.narrativas as Record<string, unknown> | undefined;
  const charts = narrativas?.charts as Record<string, unknown> | undefined;
  const ratios = data.ratios as unknown as RatiosData | undefined;

  const estrategiaAporte = inv?.estrategia_aporte;

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

      {/* Top 15 ativos — ranking estruturado (substitui NarrativeChartCard). */}
      <Top15AtivosCard data={inv} />
      <NarrativeChartCard
        chartId="cenarios_conjuge"
        title="Cenários de Estresse — Sem renda do cônjuge"
        narratives={charts}
        fallbackConclusion={deriveChartConclusion("cenarios_conjuge", data)}
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

      {/* Track T06 · ADR-191 — card Rentabilidade rebrandeado (TRS efetiva
          full-width com cobertura essencial + ano-base + defasagem). */}
      <RentabilidadeCard ratios={ratios} />

      {/* v2.8 (ADR-148) — comparisons + changelog vs relatório anterior. */}
      <SectionSnapshotDiff sectionId="S3" data={data} />
    </ReportSection>
  );
}
