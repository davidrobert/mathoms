"use client";

import { ReportSection } from "../ReportSection";
import { ReportCard } from "../ReportCard";
import { NarrativeChartCard } from "../charts/NarrativeChartCard";
import { MonetaryValue } from "../MonetaryValue";
import type { ReportAnalysisData } from "@/lib/api";

function getCharts(data: ReportAnalysisData) {
  return (data.narrativas as Record<string, unknown> | undefined)?.charts as
    | Record<string, unknown>
    | undefined;
}

/** F9 · F2.H — U1 (Mudança EUA — F1/F2). */
export function U1MudancaEuaSection({ data }: { data: ReportAnalysisData }) {
  return (
    <ReportSection id="U1" title="Mudança EUA — Estrutura F1/F2 e Custos">
      <NarrativeChartCard
        chartId="custos_f1f2"
        title="Custos Mensais F1/F2"
        narratives={getCharts(data)}
      />
    </ReportSection>
  );
}

/** F9 · F2.H — U2 (Green Card — EB2-NIW). */
export function U2GreenCardSection({ data }: { data: ReportAnalysisData }) {
  return (
    <ReportSection id="U2" title="Green Card — EB2-NIW e Compliance">
      <NarrativeChartCard
        chartId="cenarios_cambiais"
        title="Cenários Cambiais"
        narratives={getCharts(data)}
      />
    </ReportSection>
  );
}

/** F9 · F2.H — U3 (NCLEX Roadmap). */
export function U3NclexSection({ data: _data }: { data: ReportAnalysisData }) {
  return (
    <ReportSection id="U3" title="NCLEX Roadmap — Licenciamento RN">
      <ReportCard variant="feature" title="NCLEX Roadmap">
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Roadmap de licenciamento NCLEX-RN será detalhado conforme o
          progresso da aplicação.
        </p>
      </ReportCard>
    </ReportSection>
  );
}

/** F9 · F2.H — U4 (Simulação Mariana Sem Trabalhar). */
export function U4SimulacaoMarianaSection({
  data,
}: {
  data: ReportAnalysisData;
}) {
  const cenarios = data.cenarios_mariana as
    | {
        labels?: string[];
        aportes?: number[];
        prazos_if?: number[];
        anos_if?: number[];
        idade_david_if?: number[];
      }
    | undefined;

  return (
    <ReportSection id="U4" title="Simulação — Cônjuge Sem Trabalhar">
      <NarrativeChartCard
        chartId="mariana_cenarios_usa"
        title="Cenários IF — Cônjuge"
        narratives={getCharts(data)}
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
