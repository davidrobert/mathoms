/**
 * v2.4 · Report Premium UI — Tático T2 (Aportes e Investimentos).
 *
 * Adapter puro: extrai `dashboard.aportes` + `dashboard.investimentos_delta`
 * do snapshot E5 e devolve shapes prontos para a UI. Determinístico,
 * tipado, sem mocks. Paridade com EXEMPLO_DE_RELATORIO.html `dash-aportes`.
 */
import type {
  AporteItem,
  DashboardData,
  InvestimentoDeltaItem,
} from "@/types/report-analysis";
import type { ReportAnalysisData } from "@/lib/api";

export interface AporteCard {
  readonly id: string;
  readonly label: string;
  readonly feito: boolean;
  readonly valor_meta: number;
  readonly valor_efetivo: number | null;
}

export interface AporteSummary {
  readonly cards: readonly AporteCard[];
  readonly total_meta: number;
  readonly total_realizado: number;
  readonly destinos_total: number;
  readonly destinos_concluidos: number;
}

export interface InvestimentoDeltaRow {
  readonly id: string;
  readonly label: string;
  readonly anterior: number;
  readonly atual: number;
  readonly delta: number;
}

function getDashboard(data: ReportAnalysisData): DashboardData | null {
  const dash = data.dashboard;
  if (dash === undefined || dash === null || typeof dash !== "object") return null;
  return dash as DashboardData;
}

function toCard(id: string, item: AporteItem): AporteCard {
  const efetivo = item.feito ? (item.valor_feito ?? item.valor_meta) : null;
  return {
    id,
    label: item.label,
    feito: item.feito,
    valor_meta: item.valor_meta,
    valor_efetivo: efetivo,
  };
}

/** Deriva resumo de aportes a partir de `dashboard.aportes`.
 *
 * Retorna `null` quando o snapshot não trouxer o bloco — caller renderiza
 * estado vazio.
 */
export function deriveAporteSummary(data: ReportAnalysisData): AporteSummary | null {
  const dash = getDashboard(data);
  const aportes = dash?.aportes;
  if (!aportes || Object.keys(aportes).length === 0) return null;

  const cards = Object.entries(aportes).map(([id, item]) => toCard(id, item));
  const total_meta = cards.reduce((sum, c) => sum + c.valor_meta, 0);
  const total_realizado = cards.reduce(
    (sum, c) => sum + (c.valor_efetivo ?? 0),
    0,
  );
  const destinos_concluidos = cards.filter((c) => c.feito).length;

  return {
    cards,
    total_meta,
    total_realizado,
    destinos_total: cards.length,
    destinos_concluidos,
  };
}

function toDeltaRow(id: string, item: InvestimentoDeltaItem): InvestimentoDeltaRow {
  return {
    id,
    label: item.label,
    anterior: item.anterior,
    atual: item.atual,
    delta: item.atual - item.anterior,
  };
}

/** Deriva linhas da tabela "Variação Patrimonial por Bloco". */
export function deriveInvestimentosDelta(
  data: ReportAnalysisData,
): readonly InvestimentoDeltaRow[] {
  const dash = getDashboard(data);
  const delta = dash?.investimentos_delta;
  if (!delta) return [];
  return Object.entries(delta).map(([id, item]) => toDeltaRow(id, item));
}
