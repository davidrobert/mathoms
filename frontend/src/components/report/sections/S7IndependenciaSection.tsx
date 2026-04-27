"use client";

import { ReportSection } from "../ReportSection";
import { SectionSummary } from "../SectionSummary";
import { PrevidenciaPgblCard, type PrevidenciaPgblData } from "../cards";
import { NarrativeChartCard } from "../charts/NarrativeChartCard";
import { MonetaryValue } from "../MonetaryValue";
import { deriveChartConclusion } from "../utils/conclusionUtils";
import type { ReportAnalysisData } from "@/lib/api";

/** F9 · F2.E — Seção S7 (Independência Financeira). */
export function S7IndependenciaSection({ data }: { data: ReportAnalysisData }) {
  const narrativas = data.narrativas as Record<string, unknown> | undefined;
  const charts = narrativas?.charts as Record<string, unknown> | undefined;
  const previdencia = data.previdencia_pgbl as unknown as PrevidenciaPgblData | undefined;
  const goals = data.goals as Record<string, unknown> | undefined;

  return (
    <ReportSection id="S7" title="Independência Financeira — Projeção de Longo Prazo">
      <SectionSummary narrativas={narrativas} sectionId="S7" />
      <NarrativeChartCard
        chartId="projecao_3cenarios"
        title="Projeção Patrimonial — 3 Cenários"
        narratives={charts}
        fallbackConclusion={deriveChartConclusion("projecao_3cenarios", data)}
      />
      <NarrativeChartCard
        chartId="renda_passiva"
        title="Renda Passiva — Progresso até a Meta"
        narratives={charts}
        fallbackConclusion={deriveChartConclusion("renda_passiva", data)}
      />

      {goals && (
        <div className="md:col-span-2 grid grid-cols-2 gap-4 md:grid-cols-4">
          <Stat label="Meta IF" value={<MonetaryValue value={goals.if_meta as number | undefined} compact />} />
          <Stat label="Progresso" value={`${((goals.if_pct as number) ?? 0).toFixed(1)}%`} />
          <Stat label="Ano projetado" value={String(goals.ano_if ?? "—")} />
          <Stat label="Gap" value={<MonetaryValue value={goals.if_gap as number | undefined} compact />} />
        </div>
      )}

      <div className="md:col-span-2">
        <PrevidenciaPgblCard previdencia={previdencia} />
      </div>
    </ReportSection>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-[var(--radius-card)] border border-[var(--surface-border)] bg-[var(--surface-card)] p-4">
      <p className="text-xs uppercase tracking-wider text-[var(--surface-muted-foreground)]">{label}</p>
      <p className="mt-1 text-lg font-semibold">{value}</p>
    </div>
  );
}
