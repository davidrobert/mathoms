"use client";

import { ReportSection } from "../ReportSection";
import { SectionSummary } from "../SectionSummary";
import { NarrativeChartCard } from "../charts/NarrativeChartCard";
import { deriveChartConclusion, deriveSectionSummary } from "../utils/conclusionUtils";
import type { ReportAnalysisData } from "@/lib/api";

/** F9 · F2.D · ADR-117 — Seção S4 (Real Estate — Imóveis e Renda Passiva). */
export function S4RealEstateSection({ data }: { data: ReportAnalysisData }) {
  const narrativas = data.narrativas as Record<string, unknown> | undefined;
  const charts = narrativas?.charts as Record<string, unknown> | undefined;
  const fallback = deriveSectionSummary("S4", data);

  return (
    <ReportSection id="S4" title="Real Estate — Imóveis e Renda Passiva">
      <SectionSummary narrativas={narrativas} sectionId="S4" />
      {fallback && !narrativas?.["S4"] && (
        <p className="md:col-span-2 text-sm text-[var(--surface-muted-foreground)]">
          {fallback}
        </p>
      )}
      <NarrativeChartCard
        chartId="yield_imoveis"
        title="Rentabilidade dos Imóveis (Yield) vs CDI"
        narratives={charts}
        fallbackConclusion={deriveChartConclusion("yield_imoveis", data)}
      />
    </ReportSection>
  );
}
