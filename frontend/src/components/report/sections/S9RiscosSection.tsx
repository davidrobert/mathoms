"use client";

import { ShieldOff } from "lucide-react";

import { EmptyState } from "@/components/EmptyState";
import type { ReportAnalysisData } from "@/lib/api";

import { NarrativeChartCard } from "../charts/NarrativeChartCard";
import { ReportSection } from "../ReportSection";
import { SectionSummary } from "../SectionSummary";
import { deriveChartConclusion, deriveSectionSummary } from "../utils/conclusionUtils";

/** F9 · F2.F · ADR-117 / ADR-192 T01 — Seção S9 (Riscos e Proteção). */
export function S9RiscosSection({ data }: { data: ReportAnalysisData }) {
  const narrativas = data.narrativas as Record<string, unknown> | undefined;
  const charts = narrativas?.charts as Record<string, unknown> | undefined;
  const bubble = charts?.bubble_riscos as { data_state?: string } | undefined;
  const fallback = deriveSectionSummary("S9", data);
  const isEmpty = bubble?.data_state === "empty";

  return (
    <ReportSection id="S9" title="Riscos e Proteção — Seguros Críticos">
      <SectionSummary narrativas={narrativas} sectionId="S9" />
      {fallback && !narrativas?.["S9"] && (
        <p className="md:col-span-2 text-sm text-[var(--surface-muted-foreground)]">
          {fallback}
        </p>
      )}
      {isEmpty ? (
        <div className="md:col-span-2">
          <EmptyState
            icon={ShieldOff}
            title="Mapeie seus riscos críticos para destravar esta seção"
            description="Sem riscos cadastrados, não conseguimos calcular cobertura recomendada, exposição de compliance ou planejamento sucessório. Registre vida, invalidez, sucessão e compliance no Console para a análise completa."
            action={{ href: "/plano", label: "Cadastrar riscos no Console" }}
          />
        </div>
      ) : (
        <NarrativeChartCard
          chartId="bubble_riscos"
          title="Mapa de Riscos"
          narratives={charts}
          fallbackConclusion={deriveChartConclusion("bubble_riscos", data)}
        />
      )}
    </ReportSection>
  );
}
