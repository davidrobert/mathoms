"use client";

import { ReportSection } from "../ReportSection";
import { SectionSummary } from "../SectionSummary";
import { PontosFortesCard, PontosUrgentesCard } from "../cards";
import { NarrativeChartCard } from "../charts/NarrativeChartCard";
import { deriveChartConclusion } from "../utils/conclusionUtils";
import type { ReportAnalysisData } from "@/lib/api";

/** F9 · F2.G · ADR-117 — Seção S10 (Síntese Estratégica).
 *
 * O Score Financeiro vive em S1 (`report_layout.yaml` §estrategico.S1.charts.score_gauge);
 * S10 sintetiza decisões + pontos fortes/urgentes — sem duplicar o gauge.
 */
export function S10SinteseSection({ data }: { data: ReportAnalysisData }) {
  const narrativas = data.narrativas as Record<string, unknown> | undefined;
  const charts = narrativas?.charts as Record<string, unknown> | undefined;

  return (
    <ReportSection id="S10" title="Síntese Estratégica — Tarefas e Score">
      <SectionSummary data={data} sectionId="S10" />

      <div className="md:col-span-2">
        {/* A37.l14 (PD-02): título neutro — "Top 5" hardcoded mentia quando
            o workspace tinha menos decisões (a narrativa já traz a contagem). */}
        <NarrativeChartCard
          chartId="top5_decisoes"
          title="Decisões de Impacto"
          narratives={charts}
          fallbackConclusion={deriveChartConclusion("top5_decisoes", data)}
        />
      </div>

      <PontosFortesCard pontos={data.pontos_fortes as unknown[] | undefined} />
      <PontosUrgentesCard pontos={data.pontos_urgentes as unknown[] | undefined} />
    </ReportSection>
  );
}
