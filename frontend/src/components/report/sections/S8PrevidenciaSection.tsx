"use client";

import { ReportSection } from "../ReportSection";
import { SectionSummary } from "../SectionSummary";
import { CascataFiscalCard } from "../cards/CascataFiscalCard";
import type { ReportAnalysisData, TributarioBundle } from "@/lib/api";

/** F9 · F2.F · ADR-117 — Seção S8 (Previdência — PGBL e Fiscalidade).
 *
 * Sprint A16 L2 P5 (ADR-236 §D5) — substitui `<NarrativeChartCard
 * chartId="impostos_pj"/>` por `<CascataFiscalCard/>` que renderiza a
 * cascata calculada (P3) + triggers (P3) + PGBL block. Card lê
 * `data.tributario` (exposto no E5 output pelo wiring em P5).
 */
export function S8PrevidenciaSection({ data }: { data: ReportAnalysisData }) {
  const tributario = data.tributario as TributarioBundle | undefined;

  return (
    <ReportSection id="S8" title="Previdência — PGBL e Fiscalidade">
      {/* ADR-356: o fallback determinístico é a camada 3 de <SectionSummary>;
          o bloco separado (com guarda `!narrativas?.["S8"]`) foi deletado —
          com render site único, o duplo-parágrafo é impossível. */}
      <SectionSummary data={data} sectionId="S8" />
      <CascataFiscalCard tributario={tributario} />
    </ReportSection>
  );
}
