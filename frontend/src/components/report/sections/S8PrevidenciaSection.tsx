"use client";

import { ReportSection } from "../ReportSection";
import { NarrativeChartCard } from "../charts/NarrativeChartCard";
import type { ReportAnalysisData } from "@/lib/api";

/** F9 · F2.F — Seção S8 (Previdência — PGBL e Fiscalidade). */
export function S8PrevidenciaSection({ data }: { data: ReportAnalysisData }) {
  const charts = (data.narrativas as Record<string, unknown> | undefined)?.charts as Record<string, unknown> | undefined;

  return (
    <ReportSection id="S8" title="Previdência — PGBL e Fiscalidade">
      <NarrativeChartCard chartId="impostos_pj" title="Tributário PJ — Cascata Fiscal" narratives={charts} />
    </ReportSection>
  );
}
