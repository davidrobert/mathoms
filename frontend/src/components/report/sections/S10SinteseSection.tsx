"use client";

import { ReportSection } from "../ReportSection";
import { PontosFortesList } from "../cards/PontosFortesList";
import { PontosUrgentesList } from "../cards/PontosUrgentesList";
import { NarrativeChartCard } from "../charts/NarrativeChartCard";
import type { ReportAnalysisData } from "@/lib/api";

/** F9 · F2.G — Seção S10 (Síntese Estratégica — Tarefas e Score). */
export function S10SinteseSection({ data }: { data: ReportAnalysisData }) {
  const charts = (data.narrativas as Record<string, unknown> | undefined)?.charts as Record<string, unknown> | undefined;

  return (
    <ReportSection id="S10" title="Síntese Estratégica — Tarefas e Score">
      <NarrativeChartCard chartId="top5_decisoes" title="Top 5 Decisões de Impacto" narratives={charts} />
      <PontosFortesList pontos={data.pontos_fortes as unknown[] | undefined} />
      <PontosUrgentesList pontos={data.pontos_urgentes as unknown[] | undefined} />
    </ReportSection>
  );
}
