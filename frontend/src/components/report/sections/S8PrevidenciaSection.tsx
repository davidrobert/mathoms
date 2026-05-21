"use client";

import { ReportSection } from "../ReportSection";
import { SectionSummary } from "../SectionSummary";
import { CascataFiscalCard } from "../cards/CascataFiscalCard";
import { deriveSectionSummary } from "../utils/conclusionUtils";
import type { ReportAnalysisData, TributarioBundle } from "@/lib/api";

/** F9 · F2.F · ADR-117 — Seção S8 (Previdência — PGBL e Fiscalidade).
 *
 * Sprint A16 L2 P5 (ADR-236 §D5) — substitui `<NarrativeChartCard
 * chartId="impostos_pj"/>` por `<CascataFiscalCard/>` que renderiza a
 * cascata calculada (P3) + triggers (P3) + PGBL block. Card lê
 * `data.tributario` (exposto no E5 output pelo wiring em P5).
 */
export function S8PrevidenciaSection({ data }: { data: ReportAnalysisData }) {
  const narrativas = data.narrativas as Record<string, unknown> | undefined;
  const tributario = data.tributario as TributarioBundle | undefined;
  const fallback = deriveSectionSummary("S8", data);

  return (
    <ReportSection id="S8" title="Previdência — PGBL e Fiscalidade">
      <SectionSummary narrativas={narrativas} sectionId="S8" />
      {fallback && !narrativas?.["S8"] && (
        <p className="md:col-span-2 text-sm text-[var(--surface-muted-foreground)]">
          {fallback}
        </p>
      )}
      <CascataFiscalCard tributario={tributario} />
    </ReportSection>
  );
}
