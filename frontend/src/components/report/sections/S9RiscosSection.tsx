"use client";

import { ReportSection } from "../ReportSection";
import { SectionSummary } from "../SectionSummary";
import { NarrativeChartCard } from "../charts/NarrativeChartCard";
import type { ReportAnalysisData } from "@/lib/api";

/** F9 · F2.F — Seção S9 (Riscos e Proteção — Seguros Críticos). */
export function S9RiscosSection({ data }: { data: ReportAnalysisData }) {
  const narrativas = data.narrativas as Record<string, unknown> | undefined;
  const charts = narrativas?.charts as Record<string, unknown> | undefined;

  return (
    <ReportSection id="S9" title="Riscos e Proteção — Seguros Críticos">
      <SectionSummary narrativas={narrativas} sectionId="S9" />
      <NarrativeChartCard chartId="bubble_riscos" title="Mapa de Riscos" narratives={charts} />
    </ReportSection>
  );
}
