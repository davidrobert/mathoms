"use client";

import type { ReportAnalysisData } from "@/lib/api";
import { ReportSection } from "../ReportSection";
import { SectionSummary } from "../SectionSummary";
import { NarrativeChartCard } from "../charts/NarrativeChartCard";
import { RealEstateYieldCard } from "../cards/RealEstateYieldCard";
import { deriveChartConclusion, deriveSectionSummary } from "../utils/conclusionUtils";

/** S4 (Real Estate). ADR-216 Onda 2 P-C — RealEstateYieldCard quando `real_estate` presente;
 *  fallback para NarrativeChartCard legado quando workspace sem property_identity (Onda 0). */
export function S4RealEstateSection({ data }: { data: ReportAnalysisData }) {
  const narrativas = data.narrativas as Record<string, unknown> | undefined;
  const charts = narrativas?.charts as Record<string, unknown> | undefined;
  const fallback = deriveSectionSummary("S4", data);
  const realEstate = data.real_estate ?? null;

  return (
    <ReportSection id="S4" title="Real Estate — Imóveis e Renda Passiva">
      <SectionSummary narrativas={narrativas} sectionId="S4" />
      {fallback && !narrativas?.["S4"] && (
        <p className="md:col-span-2 text-sm text-[var(--surface-muted-foreground)]">
          {fallback}
        </p>
      )}
      {realEstate ? (
        <RealEstateYieldCard data={realEstate} />
      ) : (
        <NarrativeChartCard
          chartId="yield_imoveis"
          title="Rentabilidade dos Imóveis (Yield) vs CDI"
          narratives={charts}
          fallbackConclusion={deriveChartConclusion("yield_imoveis", data)}
        />
      )}
    </ReportSection>
  );
}
