"use client";

import { ReportSection } from "../ReportSection";
import { SectionSummary } from "../SectionSummary";
import { PontosFortesCard, PontosUrgentesCard } from "../cards";
import { NarrativeChartCard } from "../charts/NarrativeChartCard";
import { ScoreCard } from "../ui/ScoreCard";
import type { ScoreClasse, ScoreBreakdownRow } from "../ui/ScoreCard";
import { ChartConclusion } from "../charts/primitives";
import {
  deriveChartConclusion,
  deriveSectionSummary,
} from "../utils/conclusionUtils";
import type { ReportAnalysisData } from "@/lib/api";

/** F9 · F2.G · ADR-117 — Seção S10 (Síntese Estratégica). */
export function S10SinteseSection({ data }: { data: ReportAnalysisData }) {
  const narrativas = data.narrativas as Record<string, unknown> | undefined;
  const charts = narrativas?.charts as Record<string, unknown> | undefined;

  const score = pickScoreCard(data);
  const summaryFallback = deriveSectionSummary("S10", data);
  const chartConclusion = deriveChartConclusion("top5_decisoes", data);

  return (
    <ReportSection id="S10" title="Síntese Estratégica — Tarefas e Score">
      <SectionSummary narrativas={narrativas} sectionId="S10" />
      {/* Fallback determinístico quando E5.N não gerou narrativa para S10. */}
      {summaryFallback && !narrativas?.["S10"] && (
        <p className="md:col-span-2 text-sm text-[var(--surface-muted-foreground)]">
          {summaryFallback}
        </p>
      )}

      {score && (
        <div className="md:col-span-2">
          <ScoreCard
            value={score.value}
            max={score.max}
            classe={score.classe}
            breakdown={score.breakdown}
            formula={score.formula}
          />
        </div>
      )}

      <div className="md:col-span-2">
        <NarrativeChartCard
          chartId="top5_decisoes"
          title="Top 5 Decisões de Impacto"
          narratives={charts}
        />
        {chartConclusion && <ChartConclusion>{chartConclusion}</ChartConclusion>}
      </div>

      <PontosFortesCard pontos={data.pontos_fortes as unknown[] | undefined} />
      <PontosUrgentesCard pontos={data.pontos_urgentes as unknown[] | undefined} />
    </ReportSection>
  );
}

// ─── Score adapter ──────────────────────────────────────────────────

type ScoreComponent = { nome?: unknown; valor?: unknown; peso?: unknown; nota?: unknown };

function pickScoreCard(data: ReportAnalysisData): {
  value: number;
  max: number;
  classe: ScoreClasse;
  breakdown: ScoreBreakdownRow[];
  formula?: string;
} | null {
  const raw = data.score as
    | {
        valor?: number;
        max?: number;
        classificacao?: string;
        componentes?: unknown[];
        formula?: string;
      }
    | undefined;
  if (!raw || typeof raw.valor !== "number" || typeof raw.max !== "number") {
    return null;
  }
  return {
    value: raw.valor,
    max: raw.max,
    classe: normalizeClasse(raw.classificacao),
    breakdown: (raw.componentes ?? [])
      .map((c): ScoreBreakdownRow | null => {
        const comp = c as ScoreComponent;
        if (typeof comp.nome !== "string") return null;
        const valor = typeof comp.nota === "number" ? comp.nota : Number(comp.nota);
        if (!isFinite(valor)) return null;
        const peso = typeof comp.peso === "number" ? comp.peso : undefined;
        return {
          dimensao: comp.nome,
          valor,
          max: raw.max,
          peso,
          contribuicao: peso !== undefined ? valor * peso : undefined,
        };
      })
      .filter((row): row is ScoreBreakdownRow => row !== null),
    formula: raw.formula,
  };
}

function normalizeClasse(s: string | undefined): ScoreClasse {
  const known: readonly ScoreClasse[] = [
    "Excelente",
    "Bom",
    "Regular",
    "Ruim",
    "Péssimo",
    "Crítico",
  ];
  if (s && (known as readonly string[]).includes(s)) return s as ScoreClasse;
  return "Regular";
}
