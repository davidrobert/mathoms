"use client";

import type { ReportAnalysisData } from "@/lib/api";
import { ReportSection } from "../ReportSection";
import { SectionSummary } from "../SectionSummary";
import { RealEstateYieldCard } from "../cards/RealEstateYieldCard";

/** S4 (Real Estate). ADR-216 Onda 6 — cutover: NarrativeChartCard removido;
 *  RealEstateYieldCard é o único renderer. Seção é ocultada quando workspace
 *  não tem property_identity (data.real_estate === null) e não há narrativa S4. */
export function S4RealEstateSection({ data }: { data: ReportAnalysisData }) {
  const narrativas = data.narrativas as Record<string, unknown> | undefined;
  const realEstate = data.real_estate ?? null;
  const hasS4Narrativa = Boolean(narrativas?.["S4"]);

  if (!realEstate && !hasS4Narrativa) {
    return null;
  }

  return (
    <ReportSection id="S4" title="Real Estate — Imóveis e Renda Passiva">
      <SectionSummary narrativas={narrativas} sectionId="S4" />
      {realEstate && <RealEstateYieldCard data={realEstate} />}
    </ReportSection>
  );
}
