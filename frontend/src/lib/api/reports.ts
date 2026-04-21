import { API_BASE, apiFetch } from "./core";

// ─── Report Types ───

export interface ReportResponse {
  id: string;
  workspace_id: string;
  title: string;
  period: string | null;
  size_bytes: number | null;
  score: number | null;
  patrimonio_liquido: number | null;
  created_at: string;
  /** F11.4a — execução do pipeline que gerou o snapshot (se houver). */
  pipeline_run_id: string | null;
  /** F11.4a — documentos prontos no workspace (agregado; IDs truncados no backend). */
  source_document_count: number;
  source_document_ids: string[];
  /** F9 · ADR-076 — true se o relatório tem JSON de análise p/ render nativo. */
  has_analysis_data: boolean;
  /** F11.6b — snapshot de premissas (hash goals.json + metas ativas) na geração. */
  premissas_snapshot?: Record<string, unknown> | null;
}

export interface ReportListResponse {
  reports: ReportResponse[];
  total: number;
}

/** F9 · ADR-076 — payload do GET /reports/{id}/data.
 *
 * Tipagem progressiva: as 24 chaves top-level do E5 JSON serão tipadas
 * fortemente conforme as seções forem migradas nos lotes 2.A–2.H. Nesta
 * fase (F0.5) expomos shape parcial + fallback `Record<string, unknown>`.
 */
export interface ReportAnalysisData {
  /** F11.4a — injetado pelo GET /reports/{id}/data (não faz parte do E5 legado). */
  _report_lineage?: {
    pipeline_run_id: string | null;
    source_document_count: number;
    source_document_ids: string[];
  };
  periodo_dados?: string;
  data_analise?: string;
  patrimonio?: Record<string, unknown>;
  goals?: Record<string, unknown>;
  fluxo_caixa?: Record<string, unknown>;
  ratios?: Record<string, unknown>;
  score?: {
    valor: number;
    max: number;
    classificacao?: string;
    componentes?: unknown[];
  };
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
  cenarios_mariana?: Record<string, unknown>;
  programa_milhas?: Record<string, unknown>;
  alertas?: unknown[];
  consumo_consciente?: Record<string, unknown>;
  narrativas?: Record<string, unknown>;
  review_metadata?: Record<string, unknown>;
  // Extensibilidade para chaves ainda não tipadas
  [key: string]: unknown;
}

// ─── Reports ───

export async function listReports(workspaceId: string): Promise<ReportListResponse> {
  return apiFetch(`/workspaces/${workspaceId}/reports`);
}

export async function getReport(workspaceId: string, reportId: string): Promise<ReportResponse> {
  return apiFetch(`/workspaces/${workspaceId}/reports/${reportId}`);
}

export function getReportHtmlUrl(workspaceId: string, reportId: string): string {
  return `${API_BASE}/workspaces/${workspaceId}/reports/${reportId}/html`;
}

/** F9 · F1.5 — URL de download do HTML standalone (E6). Preservado como
 *  produto para compartilhamento offline (contador, anexo, backup). */
export function getReportDownloadHtmlUrl(workspaceId: string, reportId: string): string {
  return `${API_BASE}/workspaces/${workspaceId}/reports/${reportId}/download.html`;
}

/** F9 · F4.2 — URL de download do PDF server-side (Playwright). */
export function getReportDownloadPdfUrl(workspaceId: string, reportId: string): string {
  return `${API_BASE}/workspaces/${workspaceId}/reports/${reportId}/download.pdf`;
}

/** F9 · ADR-076 — Busca o snapshot E5 JSON para o render nativo.
 *
 * Retorna 404 se o relatório é pré-F9 (sem analysis_json_path) — verifique
 * antes via `ReportResponse.has_analysis_data` para evitar a requisição.
 */
export async function getReportData(workspaceId: string, reportId: string): Promise<ReportAnalysisData> {
  return apiFetch(`/workspaces/${workspaceId}/reports/${reportId}/data`);
}
