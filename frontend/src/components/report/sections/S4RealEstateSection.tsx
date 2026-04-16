"use client";

import { ReportSection } from "../ReportSection";
import { NarrativeChartCard } from "../charts/NarrativeChartCard";
import type { ReportAnalysisData } from "@/lib/api";

/** F9 · F2.D — Seção S4 (Real Estate — Imóveis e Renda Passiva). */
export function S4RealEstateSection({ data }: { data: ReportAnalysisData }) {
  const charts = (data.narrativas as Record<string, unknown> | undefined)?.charts as Record<string, unknown> | undefined;

  return (
    <ReportSection id="S4" title="Real Estate — Imóveis e Renda Passiva">
      <NarrativeChartCard chartId="yield_imoveis" title="Rentabilidade dos Imóveis (Yield) vs CDI" narratives={charts} />
    </ReportSection>
  );
}
