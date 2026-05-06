import type { ScoreData } from "@/types/report-analysis";
import { API_BASE, apiFetch } from "./core";

// ─── Report Types ───

export interface ReportResponse {
  id: string;
  workspace_id: string;
  title: string;
  period: string | null;
  score: number | null;
  patrimonio_liquido: number | null;
  created_at: string;
  /** F11.4a — execução do pipeline que gerou o snapshot (se houver). */
  pipeline_run_id: string | null;
  /** F11.4a — documentos prontos no workspace (agregado; IDs truncados no backend). */
  source_document_count: number;
  source_document_ids: string[];
  /** Documentos efetivamente extraídos pela run (DISTINCT document_id em pipeline_artifacts). */
  consumed_document_count: number;
  consumed_document_ids: string[];
  /** F9 · ADR-076 · ADR-131 — true se o relatório tem JSON de análise (FK ao pipeline_artifact) p/ render nativo. */
  has_analysis_data: boolean;
  /** F11.6b — snapshot de premissas (hash goals.json + metas ativas) na geração. */
  premissas_snapshot?: Record<string, unknown> | null;
  /** v2.F.3 — sobrenome da família (do workspace) para badge/cover. Pode vir
   * `null` quando o workspace não definiu sobrenome ou pré v2.F.3a. */
  workspace_family_surname?: string | null;
}

export interface ReportListResponse {
  reports: ReportResponse[];
  total: number;
}

/** v2.8 (ADR-148) — Item de comparação seção-a-seção entre relatórios. */
export interface ComparisonItemRead {
  section_id: string;
  section_label: string;
  before: number;
  after: number;
  delta_pct: number | null;
  delta_signal: "up" | "down" | "stable";
}

/** v2.8 (ADR-148) — Entrada do changelog determinístico (uma por seção). */
export interface ChangelogEntryRead {
  section_id: string;
  summary: string;
  delta_signal: "up" | "down" | "stable";
  delta_pct: number | null;
}

/** F9 · ADR-076 — payload do GET /reports/{id}/data.
 *
 * Tipagem progressiva: as 24 chaves top-level do E5 JSON serão tipadas
 * fortemente conforme as seções forem migradas nos lotes 2.A–2.H. Nesta
 * fase (F0.5) expomos shape parcial + fallback `Record<string, unknown>`.
 */
export interface ReportAnalysisData {
  /** v2.8 (ADR-148) — comparativos seção-a-seção. `null` no primeiro relatório. */
  comparisons?: ComparisonItemRead[] | null;
  /** v2.8 (ADR-148) — changelog determinístico das seções que mudaram. `null` no primeiro relatório. */
  changelog?: ChangelogEntryRead[] | null;
  /** F11.4a — injetado pelo GET /reports/{id}/data (não faz parte do E5 legado). */
  _report_lineage?: {
    pipeline_run_id: string | null;
    source_document_count: number;
    source_document_ids: string[];
    consumed_document_count: number;
    consumed_document_ids: string[];
  };
  periodo_dados?: string;
  data_analise?: string;
  patrimonio?: Record<string, unknown>;
  goals?: Record<string, unknown>;
  fluxo_caixa?: Record<string, unknown>;
  ratios?: Record<string, unknown>;
  /** v2.E.7 — score top-level tipado (absorve v2.5; elimina o cast inline em S1). */
  score?: ScoreData;
  orcamento_prospectivo?: Record<string, unknown>;
  reserva_emergencia?: Record<string, unknown>;
  endividamento?: Record<string, unknown>;
  previdencia_pgbl?: Record<string, unknown>;
  pontos_fortes?: unknown[];
  pontos_urgentes?: unknown[];
  tarefas?: unknown[];
  diagnostico_comportamental?: unknown[];
  tarefas_status?: Record<string, unknown>;
  investimentos?: Record<string, unknown>;
  equilibrio_cerbasi?: Record<string, unknown>;
  /** ADR-166 (A8.4): chave estável universal — SoT pós PR1. */
  cenarios_conjuge?: Record<string, unknown>;
  /** @deprecated ADR-166 — use `cenarios_conjuge`. Removido em PR3 (A8.4). */
  cenarios_mariana?: Record<string, unknown>;
  programa_milhas?: Record<string, unknown>;
  alertas?: unknown[];
  consumo_consciente?: Record<string, unknown>;
  narrativas?: Record<string, unknown>;
  /** v2.9 · ADR-144 — LLM-driven section summaries (id → texto). */
  section_summaries?: Record<string, string>;
  review_metadata?: Record<string, unknown>;
  /** ADR-157 — KPIs IRPF (renda, alíquota, PGBL, split trabalho×capital, evolução).
   *  Ausente quando o workspace não tem declaração IRPF processada. */
  irpf_kpis?: Record<string, unknown>;
  /** A8.3 — TRS efetiva e carteira de renda. Sempre presente; ``status``
   * controla render (ok = KPIs · sem_irpf | gerador_zero = empty state). */
  passive_income?: PassiveIncomeData;
  /** N3 — Monte Carlo IF com cone P10/P50/P90. Presente quando workspace
   * tem meta IF configurada. ``exibir_cone`` controla se o chart aparece. */
  if_monte_carlo?: IFMonteCarloData;
  // Extensibilidade para chaves ainda não tipadas
  [key: string]: unknown;
}

/** N3 — Monte Carlo IF: cone de probabilidade P10/P50/P90.
 *
 * ``exibir_cone`` false → mostrar apenas ``motivo_sem_cone`` (se presente).
 * ``caminho_p*`` são séries [ano_absoluto, valor_brl] para o Chart.js. */
export interface IFMonteCarloData {
  p10_ano_if: number | null;
  p50_ano_if: number | null;
  p90_ano_if: number | null;
  prob_if_ate_idade_meta: number;
  idade_meta_usada: number;
  sigma_usado: number;
  exibir_cone: boolean;
  motivo_sem_cone: string | null;
  caminho_p10: [number, number][];
  caminho_p50: [number, number][];
  caminho_p90: [number, number][];
}

/** A8.3 — TRS efetiva, renda passiva observada e carteira de renda.
 *
 * Renderizado em S7. ``status`` decide o caminho da UI:
 * - ``ok``: 4 KPIs + caption permanente em acumulação + banners condicionais.
 * - ``sem_irpf``: empty state com CTA "Importar IRPF".
 * - ``gerador_zero``: empty state explicando que TRS exige patrimônio investido. */
export interface PassiveIncomeData {
  status: "ok" | "sem_irpf" | "gerador_zero";
  renda_passiva_anual_brl: number;
  renda_passiva_mensal_brl: number;
  renda_passiva_por_fonte_brl: {
    dividendos: number;
    jcp: number;
    aplicacoes: number;
    ganho_capital: number;
    exterior: number;
    alugueis: number;
  };
  patrimonio_gerador_brl: number;
  trs_efetiva_pct: number;
  ano_referencia_irpf: number | null;
  defasagem_meses: number | null;
  acumuladores_pct_gerador: number;
}

// ─── Reports ───

export async function listReports(workspaceId: string): Promise<ReportListResponse> {
  return apiFetch(`/workspaces/${workspaceId}/reports`);
}

export async function getReport(workspaceId: string, reportId: string): Promise<ReportResponse> {
  return apiFetch(`/workspaces/${workspaceId}/reports/${reportId}`);
}

/** F9 · F4.2 — URL de download do PDF server-side (Playwright). */
export function getReportDownloadPdfUrl(workspaceId: string, reportId: string): string {
  return `${API_BASE}/workspaces/${workspaceId}/reports/${reportId}/download.pdf`;
}

/** F9 · ADR-076 · ADR-131 — Busca o snapshot E5 JSON para o render nativo.
 *
 * Retorna 404 se o relatório é pré-F9 ou se o artifact foi removido — verifique
 * antes via `ReportResponse.has_analysis_data` para evitar a requisição.
 */
export async function getReportData(workspaceId: string, reportId: string): Promise<ReportAnalysisData> {
  return apiFetch(`/workspaces/${workspaceId}/reports/${reportId}/data`);
}

// ─── Consumo Pontuais — gastos ≥ R$2k filtrados (transferências internas excluídas no backend) ───

export interface ConsumoPontuaisItem {
  data: string;
  descricao: string;
  valor: number;
  banco: string;
  categoria: string;
  tipo_conta?: string | null;
  titular?: string | null;
  transaction_hash: string;
}

export interface ConsumoPontuaisResponse {
  period: string;
  date_from: string;
  date_to: string;
  items: ConsumoPontuaisItem[];
  total: number;
  total_valor: number;
}

export type ConsumoPontuaisPeriod = "3m" | "6m" | "12m" | "ytd";

export async function getConsumoPontuais(
  workspaceId: string,
  period: ConsumoPontuaisPeriod,
): Promise<ConsumoPontuaisResponse> {
  return apiFetch(
    `/workspaces/${workspaceId}/reports/consumo-pontuais?period=${period}`,
  );
}
