"use client";

import { ReportSection } from "../ReportSection";
import { SectionSnapshotDiff } from "../SectionSnapshotDiff";
import { SectionSummary } from "../SectionSummary";
import {
  EndividamentoCard,
  ExposicaoCambialCard,
  PatrimonioCategoriasCard,
  ReceitasFonteCard,
  ReservaEmergenciaCard,
} from "../cards";
import { PatrimonioDoughnutChart } from "../charts/PatrimonioDoughnutChart";
import { WaterfallIfChart } from "../charts/WaterfallIfChart";
import { ScoreCard, type ScoreClasse } from "../ui/ScoreCard";
import type { ReportAnalysisData } from "@/lib/api";
import type {
  ExposicaoCambialData,
  PatrimonioData,
  ReservaEmergenciaData,
  EndividamentoData,
  FluxoCaixaSummary,
} from "@/types/report-analysis";
import { parseChartMonthLabel } from "@/lib/periodUtils";
import { deriveChartConclusion } from "../utils/conclusionUtils";

interface S1Props {
  data: ReportAnalysisData;
}

/** F9 · F2.A — Seção S1 (Patrimônio — Estrutura e Composição).
 *
 * Renderiza 3 charts + 4 cards consumindo dados do E5 JSON. Hero KPI vive
 * em `<ExecutiveSummarySection>` antes de S1 (v2.F.2).
 */
export function S1PatrimonioSection({ data }: S1Props) {
  const patrimonio = data.patrimonio as PatrimonioData | undefined;
  const reserva = data.reserva_emergencia as ReservaEmergenciaData | undefined;
  const endividamento = data.endividamento as EndividamentoData | undefined;
  const exposicaoCambial = data.exposicao_cambial as ExposicaoCambialData | undefined;
  const score = data.score;
  const fluxo = data.fluxo_caixa as FluxoCaixaSummary | undefined;
  const goals = data.goals as Record<string, unknown> | undefined;
  const narrativas = data.narrativas as
    | Record<string, { context?: string; conclusion?: string }>
    | undefined;

  /** ADR-117/122 — narrativa explícita do E5.N > fallback determinístico da Fase 6. */
  const getConclusion = (id: string): string | undefined =>
    narrativas?.[id]?.conclusion ?? deriveChartConclusion(id, data) ?? undefined;

  /** Última label do dataset mensal vira anchor para period toggle do card de
   * receitas — paridade com `usePeriodWindow` dos charts. */
  const datasetLabels = fluxo?.receita_despesa_mensal_detalhado?.labels;
  const anchorDate = datasetLabels && datasetLabels.length > 0
    ? parseChartMonthLabel(datasetLabels[datasetLabels.length - 1]) ?? undefined
    : undefined;

  return (
    <ReportSection id="S1" title="Patrimônio — Estrutura e Composição">
      <SectionSummary narrativas={narrativas} sectionId="S1" />

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
      {score && (
        <div className="md:col-span-2">
          <ScoreCard
            value={score.valor}
            max={score.max}
            classe={score.classificacao as ScoreClasse}
            breakdown={score.breakdown}
            formula={score.formula}
            context={score.context}
            // ADR-117/122 — narrativa explícita do E5.N > parágrafo emitido pelo calculator (v2.E.7).
            conclusion={narrativas?.score_gauge?.conclusion ?? score.conclusion}
          />
        </div>
      )}

      {/* Cards */}
      <div className="md:col-span-2">
        <PatrimonioCategoriasCard patrimonio={patrimonio} />
      </div>
      <ExposicaoCambialCard data={exposicaoCambial} />
      <div className="md:col-span-2">
        <ReceitasFonteCard fluxo={fluxo} anchorDate={anchorDate} />
      </div>
      <ReservaEmergenciaCard reserva={reserva} />
      <EndividamentoCard endividamento={endividamento} />

      {/* v2.8 (ADR-148) — comparisons + changelog vs relatório anterior. */}
      <SectionSnapshotDiff sectionId="S1" data={data} />
    </ReportSection>
  );
}
