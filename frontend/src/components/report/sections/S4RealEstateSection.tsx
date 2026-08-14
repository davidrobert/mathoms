"use client";

import type { ReportAnalysisData } from "@/lib/api";
import { ReportSection } from "../ReportSection";
import { SectionSummary } from "../SectionSummary";
import { RealEstateYieldCard } from "../cards/RealEstateYieldCard";
import { readRealEstateData } from "../utils/reportContractGuards";

/** S4 (Real Estate). ADR-216 Onda 6 — cutover: NarrativeChartCard removido;
 *  RealEstateYieldCard é o único renderer. Seção é ocultada quando o workspace
 *  não tem property_identity (`data.real_estate === null`).
 *
 *  ADR-356 (A40.l4): o escape "tem narrativa S4" foi removido. Ele lia
 *  `narrativas["S4"]`, chave que nenhum produtor emite — nunca foi alcançável.
 *  Com a entrega ligada, "tem narrativa" seria sempre verdadeiro (o E5.N emite
 *  `summaries.s4` sempre; `validate_narrativas` hard-falha em summary vazio),
 *  o que mataria o hide-when-empty da ADR-216 Onda 6. O dono da visibilidade é
 *  `data.real_estate`, não a prosa. */
export function S4RealEstateSection({ data }: { data: ReportAnalysisData }) {
  if (!data.real_estate) return null;
  const realEstate = readRealEstateData(data.real_estate);

  return (
    <ReportSection id="S4">
      <SectionSummary data={data} sectionId="S4" />
      <RealEstateYieldCard data={realEstate} />
    </ReportSection>
  );
}
