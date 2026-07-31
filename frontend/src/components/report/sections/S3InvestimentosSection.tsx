"use client";

import { ReportSection } from "../ReportSection";
import { SectionSummary } from "../SectionSummary";
import {
  AlocacaoAtualVsAlvoCard,
  ContrafluxoCard,
  EstrategiaAporteCard,
  ProventosYieldCard,
  RentabilidadeCard,
  Top15AtivosCard,
  type AlocacaoDerived,
  type ContrafluxoData,
  type EstrategiaAporteData,
  type InvestimentosClasseData,
  type Top15AtivosData,
} from "../cards";
import { NarrativeChartCard } from "../charts/NarrativeChartCard";
import { readNarrativeConclusion } from "../utils/chartNarrative";
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
  // ADR-141 §Emenda: o desvio é computado no backend (goals.alocacao_alvo.derived).
  // Payload E5 antigo (sem derived) → card oculto; nunca recomputar client-side.
  const alocacaoDerived = (goals?.alocacao_alvo as
    | { derived?: AlocacaoDerived }
    | undefined)?.derived;
  const alocacaoFooter = readNarrativeConclusion(charts, "alocacao_atual_vs_alvo");

  return (
    <ReportSection id="S3" title="Investimentos — Carteira Financeira">
      <SectionSummary data={data} sectionId="S3" />

      <div className="md:col-span-2">
        <AlocacaoAtualVsAlvoCard
          derived={alocacaoDerived}
          llmFooter={alocacaoFooter}
        />
      </div>

      {/* Top 15 ativos — ranking estruturado (substitui NarrativeChartCard). */}
      <Top15AtivosCard data={inv} />

      {/* A33.l4 (ADR-238 §L4) — proventos por ativo dos informes anuais.
          Sem wrapper: o card já é size="full" e retorna null (célula nenhuma)
          quando o workspace não tem informe de proventos. */}
      <ProventosYieldCard data={data.proventos_por_ativo} />
      <NarrativeChartCard
        chartId="cenarios_conjuge"
        title="Cenários de Estresse — Sem renda do cônjuge"
        narratives={charts}
        fallbackConclusion={deriveChartConclusion("cenarios_conjuge", data)}
      />

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
    </ReportSection>
  );
}
