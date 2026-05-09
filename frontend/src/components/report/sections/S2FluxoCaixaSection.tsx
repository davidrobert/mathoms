"use client";

import { ReportSection } from "../ReportSection";
import { SectionSnapshotDiff } from "../SectionSnapshotDiff";
import { SectionSummary } from "../SectionSummary";
import { SuggestionCalloutInline } from "./SuggestionCallout";
import {
  ConsumoConscienteCard,
  DiagnosticoComportamentalCard,
  EquilibrioCerbasiCard,
  OrcamentoProspectivoCard,
} from "../cards";
import { FluxoMensalChart } from "../charts/FluxoMensalChart";
import { ReceitaBarChart } from "../charts/ReceitaBarChart";
import { DespesasDoughnutChart } from "../charts/DespesasDoughnutChart";
import { ReceitaDespesaMensalChart } from "../charts/ReceitaDespesaMensalChart";
import type { ReportAnalysisData } from "@/lib/api";
import type {
  FluxoCaixaSummary,
  OrcamentoProspectivoData,
  ConsumoConscienteData,
  DiagnosticoComportamental,
  EquilibrioCerbasiData,
} from "@/types/report-analysis";
import { parseChartMonthLabel } from "@/lib/periodUtils";
import { deriveChartConclusion } from "../utils/conclusionUtils";

/** F9 · F2.B — Seção S2 (Fluxo de Caixa — Receitas e Despesas).
 *
 * 4 charts Recharts + 4 cards com dados de fluxo_caixa,
 * orcamento_prospectivo, consumo_consciente, diagnostico_comportamental,
 * equilibrio_cerbasi.
 */
export function S2FluxoCaixaSection({
  data,
  workspaceId,
}: {
  data: ReportAnalysisData;
  workspaceId?: string;
}) {
  const fluxo = data.fluxo_caixa as FluxoCaixaSummary | undefined;
  const orcamento = data.orcamento_prospectivo as
    | OrcamentoProspectivoData
    | undefined;
  const consumo = data.consumo_consciente as
    | ConsumoConscienteData
    | undefined;
  const diagnostico = data.diagnostico_comportamental as
    | DiagnosticoComportamental[]
    | undefined;
  const equilibrio = data.equilibrio_cerbasi as
    | EquilibrioCerbasiData
    | undefined;
  const narrativas = data.narrativas as
    | Record<string, { context?: string; conclusion?: string }>
    | undefined;

  const getConclusion = (id: string): string | undefined =>
    narrativas?.[id]?.conclusion ?? deriveChartConclusion(id, data) ?? undefined;

  /** Última label do dataset mensal vira anchor para period toggles dos cards
   * — paridade com `usePeriodWindow` dos charts (evita janela vazia quando
   * dados são mais antigos que "hoje"). */
  const datasetLabels = fluxo?.receita_despesa_mensal_detalhado?.labels;
  const anchorDate = datasetLabels && datasetLabels.length > 0
    ? parseChartMonthLabel(datasetLabels[datasetLabels.length - 1]) ?? undefined
    : undefined;

  return (
    <ReportSection id="S2" title="Fluxo de Caixa — Receitas e Despesas">
      <SectionSummary narrativas={narrativas} sectionId="S2" />
      {workspaceId && (
        <SuggestionCalloutInline sectionId="S2" workspaceId={workspaceId} />
      )}

      {/* Charts */}
      <div className="md:col-span-2">
        <FluxoMensalChart fluxo={fluxo} conclusion={getConclusion("fluxo_mensal")} />
      </div>
      <ReceitaBarChart fluxo={fluxo} conclusion={getConclusion("receita_fonte")} />
      <DespesasDoughnutChart fluxo={fluxo} conclusion={getConclusion("despesas_categoria")} />
      <div className="md:col-span-2">
        <ReceitaDespesaMensalChart fluxo={fluxo} />
      </div>

      {/* Cards */}
      <div className="md:col-span-2">
        <OrcamentoProspectivoCard orcamento={orcamento} anchorDate={anchorDate} />
      </div>
      <div className="md:col-span-2">
        <ConsumoConscienteCard consumo={consumo} />
      </div>
      <DiagnosticoComportamentalCard diagnostico={diagnostico} />
      <EquilibrioCerbasiCard equilibrio={equilibrio} />

      {/* v2.8 (ADR-148) — comparisons + changelog vs relatório anterior. */}
      <SectionSnapshotDiff sectionId="S2" data={data} />
    </ReportSection>
  );
}
