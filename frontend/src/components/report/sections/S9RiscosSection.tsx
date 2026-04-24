"use client";

import { ReportSection } from "../ReportSection";
import { SectionSummary } from "../SectionSummary";
import { NarrativeChartCard } from "../charts/NarrativeChartCard";
import { deriveChartConclusion, deriveSectionSummary } from "../utils/conclusionUtils";
import type { ReportAnalysisData } from "@/lib/api";

/** F9 · F2.F · ADR-117 — Seção S9 (Riscos e Proteção — Seguros Críticos). */
export function S9RiscosSection({ data }: { data: ReportAnalysisData }) {
  const narrativas = data.narrativas as Record<string, unknown> | undefined;
  const charts = narrativas?.charts as Record<string, unknown> | undefined;
  const fallback = deriveSectionSummary("S9", data);

  return (
    <ReportSection id="S9" title="Riscos e Proteção — Seguros Críticos">
      <SectionSummary narrativas={narrativas} sectionId="S9" />
      {fallback && !narrativas?.["S9"] && (
        <p className="md:col-span-2 text-sm text-[var(--surface-muted-foreground)]">
          {fallback}
        </p>
      )}
      <NarrativeChartCard
        chartId="bubble_riscos"
        title="Mapa de Riscos"
        narratives={charts}
        fallbackConclusion={deriveChartConclusion("bubble_riscos", data)}
      />
    </ReportSection>
  );
}
