"use client";

import { ShieldOff } from "lucide-react";

import { EmptyState } from "@/components/EmptyState";
import type { ReportAnalysisData } from "@/lib/api";

import {
  AcoesMitigacaoCard,
  CoberturaSegurosCard,
  HeroGapProtecaoCard,
  SucessaoCard,
  type ProtectionBundle,
} from "../cards";
import {
  NarrativeChartCard,
  type MitigationLegendItem,
} from "../charts/NarrativeChartCard";
import { ReportSection } from "../ReportSection";
import { SectionSummary } from "../SectionSummary";
import {
  deriveChartConclusion,
  deriveSectionSummary,
} from "../utils/conclusionUtils";

interface MitigationCounts {
  coberto: number;
  parcial: number;
  descoberto: number;
}

function countMitigationStatuses(
  gapAnalysis: ProtectionBundle["gap_analysis"] | undefined,
): MitigationCounts {
  const counts = { coberto: 0, parcial: 0, descoberto: 0 };
  if (!gapAnalysis) return counts;
  for (const value of Object.values(gapAnalysis)) {
    if (value.gap_brl === null || value.gap_brl === undefined) {
      if (value.actual_brl > 0) counts.coberto += 1;
    } else if (value.gap_brl > 0) {
      counts.descoberto += 1;
    } else {
      counts.coberto += 1;
    }
  }
  return counts;
}

/** Legenda canônica da 3ª dimensão (cor) do bubble `bubble_riscos`
 * — ADR-192 §D4 (re-enquadramento). Ordem: descoberto → parcial →
 * coberto. Counts injetados quando bundle disponível. */
function buildMitigationLegend(
  bundle: ProtectionBundle | undefined,
): MitigationLegendItem[] {
  const counts = countMitigationStatuses(bundle?.gap_analysis);
  const total = counts.coberto + counts.parcial + counts.descoberto;
  const has = total > 0;
  return [
    { status: "descoberto", label: "Descoberto", count: has ? counts.descoberto : undefined },
    { status: "parcial", label: "Parcial", count: has ? counts.parcial : undefined },
    { status: "coberto", label: "Coberto", count: has ? counts.coberto : undefined },
  ];
}

/** F9 · F2.F · ADR-117 / ADR-192 §D4 (S9-T04) — Seção S9 (Riscos e Proteção).
 *
 * Expandida em T04 para 5 blocos paritários com S10:
 *   - HeroGapProtecaoCard (full, KPI protagonista)
 *   - CoberturaSegurosCard (full, tabela densa)
 *   - SucessaoCard (half) + AcoesMitigacaoCard (half)
 *   - NarrativeChartCard bubble_riscos (full, re-enquadrado: apenas
 *     riscos compliance/sucessório + 3ª dimensão cor = mitigation_status)
 *
 * T01 empty state preservado: `data_state="empty"` continua renderizando
 * `<EmptyState/>` quando workspace não tem `Risk` cadastrado.
 *
 * TODO: dados reais virão de T03 — `data.protection_bundle` é populado
 * pelo adapter (ADR-192 §D2 + S9-T03 calculators). Até T03 mergear,
 * cards usam o bundle vazio (skeleton) e renderizam estados degradados
 * coerentes (gap "a calcular", checklist com pendências marcadas).
 */
export function S9RiscosSection({ data }: { data: ReportAnalysisData }) {
  const narrativas = data.narrativas as Record<string, unknown> | undefined;
  const charts = narrativas?.charts as Record<string, unknown> | undefined;
  const bubble = charts?.bubble_riscos as { data_state?: string } | undefined;
  const fallback = deriveSectionSummary("S9", data);
  const isEmpty = bubble?.data_state === "empty";

  // TODO: dados reais virão de T03 — bundle vem do payload do report
  // (E5 narrativas hidrata via `_project_protection_bundle_async`).
  // Habilitar quando merged.
  const bundle = data.protection_bundle as ProtectionBundle | undefined;
  const effectiveDate = (data.data_analise as string | undefined) ?? null;
  const mitigationLegend = buildMitigationLegend(bundle);

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
        <>
          <HeroGapProtecaoCard bundle={bundle} effectiveDate={effectiveDate} />
          <CoberturaSegurosCard bundle={bundle} effectiveDate={effectiveDate} />
          <SucessaoCard bundle={bundle} effectiveDate={effectiveDate} />
          <AcoesMitigacaoCard bundle={bundle} effectiveDate={effectiveDate} />
          <NarrativeChartCard
            chartId="bubble_riscos"
            title="Mapa de Riscos — Compliance e Sucessório"
            narratives={charts}
            fallbackConclusion={deriveChartConclusion("bubble_riscos", data)}
            mitigationLegend={mitigationLegend}
          />
        </>
      )}
    </ReportSection>
  );
}
