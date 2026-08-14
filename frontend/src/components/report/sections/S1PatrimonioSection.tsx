"use client";

import { useWorkspace } from "@/lib/WorkspaceProvider";
import { ReportSection } from "../ReportSection";
import { SectionSummary } from "../SectionSummary";
import {
  EndividamentoCard,
  ExposicaoCambialCard,
  PatrimonioCategoriasCard,
  PosicaoInformeCard,
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
import { deriveChartConclusion } from "../utils/conclusionUtils";
import { readScoreData } from "../utils/reportContractGuards";

interface S1Props {
  data: ReportAnalysisData;
  /** Pina o card de exposição cambial ao run deste relatório (ADR-379). */
  reportId?: string | null;
}

/** F9 · F2.A — Seção S1 (Patrimônio — Estrutura e Composição).
 *
 * Renderiza 3 charts + 4 cards consumindo dados do E5 JSON. Hero KPI vive
 * em `<ExecutiveSummarySection>` antes de S1 (v2.F.2).
 */
export function S1PatrimonioSection({ data, reportId }: S1Props) {
  const patrimonio = data.patrimonio as PatrimonioData | undefined;
  const reserva = data.reserva_emergencia as ReservaEmergenciaData | undefined;
  const endividamento = data.endividamento as EndividamentoData | undefined;
  const exposicaoCambial = data.exposicao_cambial as ExposicaoCambialData | undefined;
  const score = readScoreData(data.score);
  const scoreClasse = readScoreClasse(score?.classificacao);
  const fluxo = data.fluxo_caixa as FluxoCaixaSummary | undefined;
  const goals = data.goals as Record<string, unknown> | undefined;

  /** ADR-356 (A40.l4): a leitura `narrativas?.[id]` que precedia o derivado era
   * ramo morto — as conclusões do E5.N vivem em `narrativas.charts[id]`, e
   * nenhum dos 17 ids aparece no topo do bag. O comentário anterior ("narrativa
   * explícita do E5.N > fallback") descrevia um caminho inexistente. Apontar S1
   * para `narrativas.charts` fica deferido (ver ADR-356 §Deferimentos). */
  const getConclusion = (id: string): string | undefined =>
    deriveChartConclusion(id, data) ?? undefined;

  return (
    <ReportSection id="S1">
      <SectionSummary data={data} sectionId="S1" />

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
      {score && scoreClasse && (
        <div className="md:col-span-2">
          <ScoreCard
            value={score.valor}
            max={score.max}
            classe={scoreClasse}
            breakdown={score.breakdown}
            formula={score.formula}
            context={score.context}
            // ADR-356: leitura `narrativas.score_gauge` era ramo morto (o
            // produtor emite em `narrativas.charts.score_gauge`); o parágrafo
            // do calculator (v2.E.7) é a única fonte real hoje.
            conclusion={score.conclusion}
          />
        </div>
      )}

      {/* Cards */}
      <div className="md:col-span-2">
        <PatrimonioCategoriasCard patrimonio={patrimonio} />
      </div>
      {/* A33.l2 P4 (ADR-238 D5) — posição 31/12 por instituição/moeda;
          hide-when-empty (null sem posições de informe); span via size="full". */}
      <PosicaoInformeCard
        posicoes={patrimonio?.posicao_31_12}
        cbeObrigatorio={patrimonio?.cbe_obrigatorio ?? false}
      />
      <ExposicaoCambialCardWithContext
        data={exposicaoCambial}
        reportId={reportId}
      />
      <div className="md:col-span-2">
        <ReceitasFonteCard fluxo={fluxo} />
      </div>
      <ReservaEmergenciaCard reserva={reserva} />
      <EndividamentoCard endividamento={endividamento} />
    </ReportSection>
  );
}

function readScoreClasse(value: string | undefined): ScoreClasse | undefined {
  const classes: readonly ScoreClasse[] = [
    "Excelente", "Bom", "Regular", "Ruim", "Péssimo", "Crítico",
  ];
  return classes.find((item) => item === value);
}

/** Wrapper que injeta `workspaceId` do context (ADR-224 PR-E). Fora do
 * provider (ex.: testes isolados), cai pra V1 sem regressão visual. */
function ExposicaoCambialCardWithContext({
  data,
  reportId,
}: {
  data: ExposicaoCambialData | undefined;
  reportId?: string | null;
}) {
  const { workspace } = useWorkspace();
  return (
    <ExposicaoCambialCard
      data={data}
      workspaceId={workspace?.id ?? null}
      reportId={reportId}
    />
  );
}
