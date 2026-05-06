"use client";

import { ReportSection } from "../ReportSection";
import { ReportCard } from "../ReportCard";
import { SectionSummary } from "../SectionSummary";
import { NarrativeChartCard } from "../charts/NarrativeChartCard";
import { MonetaryValue } from "../MonetaryValue";
import {
  deriveChartConclusion,
  deriveSectionSummary,
} from "../utils/conclusionUtils";
import type { ReportAnalysisData } from "@/lib/api";

function getNarrativas(data: ReportAnalysisData): Record<string, unknown> | undefined {
  return data.narrativas as Record<string, unknown> | undefined;
}

function getCharts(data: ReportAnalysisData): Record<string, unknown> | undefined {
  return (getNarrativas(data)?.charts ?? undefined) as
    | Record<string, unknown>
    | undefined;
}

function SectionFallback({
  narrativas,
  sectionId,
  text,
}: {
  narrativas: Record<string, unknown> | undefined;
  sectionId: string;
  text: string | null;
}) {
  if (!text || narrativas?.[sectionId]) return null;
  return (
    <p className="md:col-span-2 text-sm text-[var(--surface-muted-foreground)]">
      {text}
    </p>
  );
}

/** F9 · Fase 9 · ADR-117/122 — U1 (Mudança EUA — F1/F2). */
export function U1MudancaEuaSection({ data }: { data: ReportAnalysisData }) {
  const narrativas = getNarrativas(data);
  const fallback = deriveSectionSummary("U1", data);
  return (
    <ReportSection id="U1" title="Mudança EUA — Estrutura F1/F2 e Custos">
      <SectionSummary narrativas={narrativas} sectionId="U1" />
      <SectionFallback narrativas={narrativas} sectionId="U1" text={fallback} />
      <NarrativeChartCard
        chartId="custos_f1f2"
        title="Custos Mensais F1/F2"
        narratives={getCharts(data)}
        fallbackConclusion={deriveChartConclusion("custos_f1f2", data)}
      />
    </ReportSection>
  );
}

/** F9 · Fase 9 · ADR-117/122 — U2 (Green Card — EB2-NIW). */
export function U2GreenCardSection({ data }: { data: ReportAnalysisData }) {
  const narrativas = getNarrativas(data);
  const fallback = deriveSectionSummary("U2", data);
  return (
    <ReportSection id="U2" title="Green Card — EB2-NIW e Compliance">
      <SectionSummary narrativas={narrativas} sectionId="U2" />
      <SectionFallback narrativas={narrativas} sectionId="U2" text={fallback} />
      <NarrativeChartCard
        chartId="cenarios_cambiais"
        title="Cenários Cambiais"
        narratives={getCharts(data)}
        fallbackConclusion={deriveChartConclusion("cenarios_cambiais", data)}
      />
    </ReportSection>
  );
}

/** F9 · Fase 9 · ADR-117/122 — U3 (NCLEX Roadmap). */
export function U3NclexSection({ data }: { data: ReportAnalysisData }) {
  const narrativas = getNarrativas(data);
  const fallback = deriveSectionSummary("U3", data);
  return (
    <ReportSection id="U3" title="NCLEX Roadmap — Licenciamento RN">
      <SectionSummary narrativas={narrativas} sectionId="U3" />
      <SectionFallback narrativas={narrativas} sectionId="U3" text={fallback} />
      <ReportCard variant="feature" title="NCLEX Roadmap">
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Roadmap de licenciamento NCLEX-RN será detalhado conforme o
          progresso da aplicação.
        </p>
      </ReportCard>
    </ReportSection>
  );
}

/** F9 · Fase 9 · ADR-117/122 — U4 (Simulação Mariana Sem Trabalhar). */
export function U4SimulacaoMarianaSection({
  data,
}: {
  data: ReportAnalysisData;
}) {
  const narrativas = getNarrativas(data);
  const fallback = deriveSectionSummary("U4", data);
  // ADR-166 (A8.4 PR3): chave estável universal `cenarios_conjuge`.
  // Esta seção inteira será deletada em PR4 (A8.4 — remoção do Modo USA).
  const cenarios = data.cenarios_conjuge as
    | {
        labels?: string[];
        aportes?: number[];
        prazos_if?: number[];
        anos_if?: number[];
      }
    | undefined;

  return (
    <ReportSection id="U4" title="Simulação — Cônjuge Sem Trabalhar">
      <SectionSummary narrativas={narrativas} sectionId="U4" />
      <SectionFallback narrativas={narrativas} sectionId="U4" text={fallback} />
      <NarrativeChartCard
        chartId="mariana_cenarios_usa"
        title="Cenários IF — Cônjuge"
        narratives={getCharts(data)}
        fallbackConclusion={deriveChartConclusion("mariana_cenarios_usa", data)}
      />
      {cenarios?.labels && cenarios.labels.length > 0 && (
        <ReportCard variant="warn" title="Cenários Comparativos">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--surface-border)] text-left">
                  <th className="pb-2 font-display font-semibold">Cenário</th>
                  <th className="pb-2 text-right font-display font-semibold">Aporte/mês</th>
                  <th className="pb-2 text-right font-display font-semibold">Prazo (anos)</th>
                  <th className="pb-2 text-right font-display font-semibold">Ano IF</th>
                </tr>
              </thead>
              <tbody>
                {cenarios.labels.map((label, i) => (
                  <tr
                    key={label}
                    className="border-b border-[var(--surface-border)]/40 last:border-0"
                  >
                    <td className="py-2">{label}</td>
                    <td className="py-2 text-right">
                      <MonetaryValue value={cenarios.aportes?.[i]} />
                    </td>
                    <td className="py-2 text-right font-mono tabular-nums">
                      {cenarios.prazos_if?.[i]?.toFixed(1) ?? "—"}
                    </td>
                    <td className="py-2 text-right font-mono tabular-nums">
                      {cenarios.anos_if?.[i] ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </ReportCard>
      )}
    </ReportSection>
  );
}
