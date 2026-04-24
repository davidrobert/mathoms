"use client";

import { ReportSection } from "../ReportSection";
import { SectionSummary } from "../SectionSummary";
import { NarrativeChartCard } from "../charts/NarrativeChartCard";
import { deriveChartConclusion, deriveSectionSummary } from "../utils/conclusionUtils";
import type { ReportAnalysisData } from "@/lib/api";

/** F9 · F2.F · ADR-117 — Seção S8 (Previdência — PGBL e Fiscalidade). */
export function S8PrevidenciaSection({ data }: { data: ReportAnalysisData }) {
  const narrativas = data.narrativas as Record<string, unknown> | undefined;
  const charts = narrativas?.charts as Record<string, unknown> | undefined;
  const fallback = deriveSectionSummary("S8", data);

  return (
    <ReportSection id="S8" title="Previdência — PGBL e Fiscalidade">
      <SectionSummary narrativas={narrativas} sectionId="S8" />
      {fallback && !narrativas?.["S8"] && (
        <p className="md:col-span-2 text-sm text-[var(--surface-muted-foreground)]">
          {fallback}
        </p>
      )}
      <NarrativeChartCard
        chartId="impostos_pj"
        title="Tributário PJ — Cascata Fiscal"
        narratives={charts}
        fallbackConclusion={deriveChartConclusion("impostos_pj", data)}
      />
    </ReportSection>
  );
}
