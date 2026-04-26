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

// ─── Report collaboration (Notes + Kanban) — ADR-123 · Fase 6.5/8 ───

export interface ReportNotesPayload {
  id: string;
  report_id: string;
  content: string;
  author_user_id: string | null;
  updated_at: string;
}

export type KanbanColuna = "a_fazer" | "em_andamento" | "concluido";
export type KanbanPrioridade = "alta" | "media" | "baixa";
export type KanbanEssencial = "S" | "R" | "O";

export interface KanbanItemPayload {
  id: string;
  report_id: string;
  titulo: string;
  coluna: KanbanColuna;
  prioridade: KanbanPrioridade | null;
  prazo: string | null;
  categoria: string | null;
  essencial: KanbanEssencial | null;
  ordem: number;
  updated_at: string;
}

export interface KanbanItemCreateBody {
  titulo: string;
  coluna?: KanbanColuna;
  prioridade?: KanbanPrioridade | null;
  prazo?: string | null;
  categoria?: string | null;
  essencial?: KanbanEssencial | null;
  ordem?: number;
}

export interface KanbanItemUpdateBody {
  titulo?: string;
  coluna?: KanbanColuna;
  prioridade?: KanbanPrioridade | null;
  prazo?: string | null;
  categoria?: string | null;
  essencial?: KanbanEssencial | null;
  ordem?: number;
}

export async function getReportNotes(
  workspaceId: string,
  reportId: string,
): Promise<ReportNotesPayload | null> {
  return apiFetch(`/workspaces/${workspaceId}/reports/${reportId}/notes`);
}

export async function putReportNotes(
  workspaceId: string,
  reportId: string,
  content: string,
): Promise<ReportNotesPayload> {
  return apiFetch(`/workspaces/${workspaceId}/reports/${reportId}/notes`, {
    method: "PUT",
    body: JSON.stringify({ content }),
  });
}

export async function listKanbanItems(
  workspaceId: string,
  reportId: string,
): Promise<{ items: KanbanItemPayload[] }> {
  return apiFetch(`/workspaces/${workspaceId}/reports/${reportId}/kanban`);
}

export async function createKanbanItem(
  workspaceId: string,
  reportId: string,
  body: KanbanItemCreateBody,
): Promise<KanbanItemPayload> {
  return apiFetch(`/workspaces/${workspaceId}/reports/${reportId}/kanban`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateKanbanItem(
  workspaceId: string,
  reportId: string,
  itemId: string,
  body: KanbanItemUpdateBody,
): Promise<KanbanItemPayload> {
  return apiFetch(
    `/workspaces/${workspaceId}/reports/${reportId}/kanban/${itemId}`,
    {
      method: "PATCH",
      body: JSON.stringify(body),
    },
  );
}

export async function deleteKanbanItem(
  workspaceId: string,
  reportId: string,
  itemId: string,
): Promise<void> {
  await apiFetch(
    `/workspaces/${workspaceId}/reports/${reportId}/kanban/${itemId}`,
    { method: "DELETE" },
  );
}
