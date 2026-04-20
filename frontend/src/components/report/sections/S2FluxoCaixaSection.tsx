"use client";

import { ReportSection } from "../ReportSection";
import { SectionSummary } from "../SectionSummary";
import { OrcamentoProspectivoCard } from "../cards/OrcamentoProspectivoCard";
import { ConsumoConscienteCard } from "../cards/ConsumoConscienteCard";
import { DiagnosticoComportamentalCard } from "../cards/DiagnosticoComportamentalCard";
import { EquilibrioCerbasiCard } from "../cards/EquilibrioCerbasiCard";
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

/** F9 · F2.B — Seção S2 (Fluxo de Caixa — Receitas e Despesas).
 *
 * 4 charts Recharts + 4 cards com dados de fluxo_caixa,
 * orcamento_prospectivo, consumo_consciente, diagnostico_comportamental,
 * equilibrio_cerbasi.
 */
export function S2FluxoCaixaSection({
  data,
}: {
  data: ReportAnalysisData;
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

  const getConclusion = (id: string) => narrativas?.[id]?.conclusion;

  return (
    <ReportSection id="S2" title="Fluxo de Caixa — Receitas e Despesas">
      <SectionSummary narrativas={narrativas} sectionId="S2" />

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
        <OrcamentoProspectivoCard orcamento={orcamento} />
      </div>
      <div className="md:col-span-2">
        <ConsumoConscienteCard consumo={consumo} />
      </div>
      <DiagnosticoComportamentalCard diagnostico={diagnostico} />
      <EquilibrioCerbasiCard equilibrio={equilibrio} />
    </ReportSection>
  );
}
