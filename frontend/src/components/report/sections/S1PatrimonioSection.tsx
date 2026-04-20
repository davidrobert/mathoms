"use client";

import { ReportSection } from "../ReportSection";
import { SectionSummary } from "../SectionSummary";
import { PatrimonioKpiRow } from "../kpi/PatrimonioKpiRow";
import { PatrimonioCategoriasCard } from "../cards/PatrimonioCategoriasCard";
import { ReceitasFonteCard } from "../cards/ReceitasFonteCard";
import { ReservaEmergenciaCard } from "../cards/ReservaEmergenciaCard";
import { EndividamentoCard } from "../cards/EndividamentoCard";
import { PatrimonioDoughnutChart } from "../charts/PatrimonioDoughnutChart";
import { WaterfallIfChart } from "../charts/WaterfallIfChart";
import { ScoreGaugeChart } from "../charts/ScoreGaugeChart";
import type { ReportAnalysisData } from "@/lib/api";
import type {
  PatrimonioData,
  ReservaEmergenciaData,
  EndividamentoData,
  RatiosData,
  ScoreData,
  FluxoCaixaSummary,
} from "@/types/report-analysis";

interface S1Props {
  data: ReportAnalysisData;
}

/** F9 · F2.A — Seção S1 completa (Patrimônio — Estrutura e Composição).
 *
 * Renderiza KPIs + 3 charts + 4 cards consumindo dados do E5 JSON.
 * Substitui a lógica de `build_sections()` do e6_render.py para S1.
 */
export function S1PatrimonioSection({ data }: S1Props) {
  const patrimonio = data.patrimonio as PatrimonioData | undefined;
  const reserva = data.reserva_emergencia as ReservaEmergenciaData | undefined;
  const endividamento = data.endividamento as EndividamentoData | undefined;
  const ratios = data.ratios as RatiosData | undefined;
  const score = data.score as ScoreData | undefined;
  const fluxo = data.fluxo_caixa as FluxoCaixaSummary | undefined;
  const goals = data.goals as Record<string, unknown> | undefined;
  const narrativas = data.narrativas as
    | Record<string, { context?: string; conclusion?: string }>
    | undefined;

  const getConclusion = (id: string) => narrativas?.[id]?.conclusion;

  return (
    <ReportSection id="S1" title="Patrimônio — Estrutura e Composição">
      <SectionSummary narrativas={narrativas} sectionId="S1" />

      {/* KPI row fora do grid 2-col (full width) */}
      <div className="md:col-span-2">
        <PatrimonioKpiRow
          patrimonio={patrimonio}
          ratios={ratios}
          score={score}
        />
      </div>

      {/* Charts */}
      <PatrimonioDoughnutChart
        patrimonio={patrimonio}
        conclusion={getConclusion("patrimonio_doughnut")}
      />
      <WaterfallIfChart
        patrimonio={patrimonio}
        goals={goals}
        conclusion={getConclusion("waterfall_if")}
      />
      <div className="md:col-span-2">
        <ScoreGaugeChart score={score} />
      </div>

      {/* Cards */}
      <div className="md:col-span-2">
        <PatrimonioCategoriasCard patrimonio={patrimonio} />
      </div>
      <div className="md:col-span-2">
        <ReceitasFonteCard fluxo={fluxo} />
      </div>
      <ReservaEmergenciaCard reserva={reserva} />
      <EndividamentoCard endividamento={endividamento} />
    </ReportSection>
  );
}
