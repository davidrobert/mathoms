const API_BASE = "/api";

// ─── Auth Types ───

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
}

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
  /** F9 · ADR-076 — true se o relatório tem JSON de análise p/ render nativo. */
  has_analysis_data: boolean;
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

// ─── Document Types ───

export type DocumentStatus =
  | "uploaded"
  | "unlocking"
  | "classifying"
  | "ready"
  | "needs_password"
  | "processing"
  | "processed"
  | "error";

export type DocumentType =
  | "bank_statement"
  | "credit_card_bill"
  | "investment_report"
  | "irpf"
  | "e1_members_json"
  | "e1_5_baseline_json"
  | "other";

export interface DocumentResponse {
  id: string;
  workspace_id: string;
  original_name: string;
  stored_path: string | null;
  doc_type: DocumentType | null;
  bank_code: string | null;
  period: string | null;
  status: DocumentStatus;
  classification_meta: Record<string, unknown> | null;
  file_size_bytes: number | null;
  content_type: string | null;
  error_message: string | null;
  uploaded_at: string;
}

export interface DocumentListResponse {
  documents: DocumentResponse[];
  total: number;
}

export interface DocumentUploadResponse {
  documents: DocumentResponse[];
  skipped_duplicates: string[];
  total_uploaded: number;
  total_skipped: number;
}

// ─── Vault Types ───

export interface VaultPasswordResponse {
  id: string;
  label: string;
  created_at: string;
}

export interface VaultListResponse {
  passwords: VaultPasswordResponse[];
  total: number;
}

// ─── Pipeline Types ───

export type PipelineRunStatus =
  | "pending"
  | "running"
  | "completed"
  | "partial_failure"
  | "failed"
  | "cancelled"
  | "needs_review"
  | "resuming";

export type PipelineStageStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "skipped"
  | "skipped_free_tier"
  | "needs_review";

export interface PipelineStageLog {
  id: string;
  stage: string;
  status: PipelineStageStatus;
  output_summary: Record<string, unknown> | null;
  errors: string | null;
  duration_ms: number | null;
  started_at: string;
  completed_at: string | null;
}

export interface PipelineRunResponse {
  id: string;
  workspace_id: string;
  status: PipelineRunStatus;
  current_stage: string | null;
  failed_at_stage: string | null;
  paused_at_stage: string | null;
  tier_at_run: string;
  total_documents: number | null;
  celery_task_id: string | null;
  started_at: string;
  completed_at: string | null;
  stage_logs: PipelineStageLog[];
}

export interface PipelineRunListResponse {
  runs: PipelineRunResponse[];
  total: number;
}

export interface PipelineEvent {
  event: string;
  run_id?: string;
  stage?: string;
  status?: string;
  progress_pct?: number;
  error?: string;
  detail?: Record<string, unknown>;
  timestamp?: string;
}

// ─── Token Management ───

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("fin_token");
}

export function setToken(token: string) {
  localStorage.setItem("fin_token", token);
}

export function clearToken() {
  localStorage.removeItem("fin_token");
}

export function isAuthenticated(): boolean {
  return !!getToken();
}

// ─── API Error ───

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string
  ) {
    super(detail);
  }
}

// ─── Fetch Helpers ───

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (
    !headers["Content-Type"] &&
    !(options.body instanceof FormData)
  ) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail || `HTTP ${res.status}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// ─── Auth ───

export async function register(
  email: string,
  password: string,
  fullName: string
): Promise<TokenResponse> {
  return apiFetch("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, full_name: fullName }),
  });
}

export async function login(
  email: string,
  password: string
): Promise<TokenResponse> {
  return apiFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function getMe(): Promise<UserResponse> {
  return apiFetch("/auth/me");
}

// ─── Reports ───

export async function listReports(): Promise<ReportListResponse> {
  return apiFetch("/reports");
}

export async function getReport(reportId: string): Promise<ReportResponse> {
  return apiFetch(`/reports/${reportId}`);
}

export function getReportHtmlUrl(reportId: string): string {
  return `${API_BASE}/reports/${reportId}/html`;
}

/** F9 · ADR-076 — Busca o snapshot E5 JSON para o render nativo.
 *
 * Retorna 404 se o relatório é pré-F9 (sem analysis_json_path) — verifique
 * antes via `ReportResponse.has_analysis_data` para evitar a requisição.
 */
export async function getReportData(reportId: string): Promise<ReportAnalysisData> {
  return apiFetch(`/reports/${reportId}/data`);
}

// ─── Documents ───

export async function uploadDocuments(
  files: File[],
  onProgress?: (loaded: number, total: number) => void
): Promise<DocumentUploadResponse> {
  const token = getToken();
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/documents/upload`);
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(e.loaded, e.total);
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        const body = JSON.parse(xhr.responseText || "{}");
        reject(new ApiError(xhr.status, body.detail || `HTTP ${xhr.status}`));
      }
    });

    xhr.addEventListener("error", () => reject(new Error("Erro de conexão")));
    xhr.send(formData);
  });
}

export async function listDocuments(
  statusFilter?: DocumentStatus,
  docTypeFilter?: DocumentType
): Promise<DocumentListResponse> {
  const params = new URLSearchParams();
  if (statusFilter) params.set("status", statusFilter);
  if (docTypeFilter) params.set("doc_type", docTypeFilter);
  const qs = params.toString();
  return apiFetch(`/documents${qs ? `?${qs}` : ""}`);
}

export async function deleteDocument(documentId: string): Promise<void> {
  return apiFetch(`/documents/${documentId}`, { method: "DELETE" });
}

export async function retryUnlock(): Promise<DocumentResponse[]> {
  return apiFetch("/documents/retry-unlock", { method: "POST" });
}

// ─── Vault ───

export async function listVaultPasswords(): Promise<VaultListResponse> {
  return apiFetch("/vault/passwords");
}

export async function createVaultPassword(
  label: string,
  password: string
): Promise<VaultPasswordResponse> {
  return apiFetch("/vault/passwords", {
    method: "POST",
    body: JSON.stringify({ label, password }),
  });
}

export async function deleteVaultPassword(passwordId: string): Promise<void> {
  return apiFetch(`/vault/passwords/${passwordId}`, { method: "DELETE" });
}

// ─── Pipeline ───

export async function triggerPipeline(opts?: {
  from_stage?: string;
  skip_llm?: boolean;
  stop_on_error?: boolean;
}): Promise<PipelineRunResponse> {
  return apiFetch("/pipeline/run", {
    method: "POST",
    body: JSON.stringify({
      from_stage: opts?.from_stage ?? null,
      skip_llm: opts?.skip_llm ?? true,
      stop_on_error: opts?.stop_on_error ?? true,
    }),
  });
}

export async function listPipelineRuns(): Promise<PipelineRunListResponse> {
  return apiFetch("/pipeline/runs");
}

export async function getPipelineRun(
  runId: string
): Promise<PipelineRunResponse> {
  return apiFetch(`/pipeline/runs/${runId}`);
}

export async function cancelPipelineRun(runId: string): Promise<void> {
  return apiFetch(`/pipeline/runs/${runId}/cancel`, { method: "POST" });
}

// ─── Config: Types ───

export interface BankAccountConfig {
  id?: string;
  institution_code: string;
  account_type: string;
  agency?: string | null;
  account_number?: string | null;
}

export interface FamilyMemberConfig {
  id?: string;
  key: string;
  full_name: string;
  short_name: string;
  cpf?: string | null;
  birth_date?: string | null;
  role: string;
  order: number;
  extra?: Record<string, unknown> | null;
  accounts: BankAccountConfig[];
}

export interface CategoryConfig {
  id?: string;
  code: string;
  name: string;
  category_type: "expense" | "income";
  monthly_cap?: number | null;
  order: number;
  keywords: string[];
}

export interface PipelineConfigData {
  llm?: Record<string, unknown> | null;
  file_limits?: Record<string, unknown> | null;
  reconciliation?: Record<string, unknown> | null;
  qa_thresholds?: Record<string, unknown> | null;
  artifact_names?: Record<string, string> | null;
  log_files?: Record<string, unknown> | null;
  period_regex?: Record<string, string> | null;
}

export interface ConfigExport {
  family_members: Record<string, unknown>;
  categorization: Record<string, unknown>;
  pipeline: Record<string, unknown>;
  institutions: Record<string, unknown>;
  report_layout: Record<string, unknown>;
}

// ─── Config: Workspace settings (family_surname etc.) ───

export interface WorkspaceSettings {
  name: string;
  family_surname: string | null;
}

export async function getWorkspaceSettings(): Promise<WorkspaceSettings> {
  return apiFetch("/config/workspace");
}

export async function updateWorkspaceSettings(
  data: Partial<Pick<WorkspaceSettings, "family_surname">>,
): Promise<WorkspaceSettings> {
  return apiFetch("/config/workspace", { method: "PATCH", body: JSON.stringify(data) });
}

// ─── Config: Members ───

export async function listMembers(): Promise<{ members: FamilyMemberConfig[]; total: number }> {
  return apiFetch("/config/members");
}

export async function createMember(data: Omit<FamilyMemberConfig, "id" | "accounts">): Promise<FamilyMemberConfig> {
  return apiFetch("/config/members", { method: "POST", body: JSON.stringify(data) });
}

export async function updateMember(id: string, data: Partial<FamilyMemberConfig>): Promise<FamilyMemberConfig> {
  return apiFetch(`/config/members/${id}`, { method: "PUT", body: JSON.stringify(data) });
}

export async function deleteMember(id: string): Promise<void> {
  return apiFetch(`/config/members/${id}`, { method: "DELETE" });
}

// ─── Config: Bank Accounts ───

export async function createBankAccount(memberId: string, data: Omit<BankAccountConfig, "id">): Promise<BankAccountConfig> {
  return apiFetch(`/config/members/${memberId}/accounts`, { method: "POST", body: JSON.stringify(data) });
}

export async function deleteBankAccount(memberId: string, accountId: string): Promise<void> {
  return apiFetch(`/config/members/${memberId}/accounts/${accountId}`, { method: "DELETE" });
}

// ─── Config: Categories ───

export async function listCategories(): Promise<{ categories: CategoryConfig[]; total: number }> {
  return apiFetch("/config/categories");
}

export async function createCategory(data: Omit<CategoryConfig, "id">): Promise<CategoryConfig> {
  return apiFetch("/config/categories", { method: "POST", body: JSON.stringify(data) });
}

export async function updateCategory(id: string, data: Partial<CategoryConfig>): Promise<CategoryConfig> {
  return apiFetch(`/config/categories/${id}`, { method: "PUT", body: JSON.stringify(data) });
}

export async function deleteCategory(id: string): Promise<void> {
  return apiFetch(`/config/categories/${id}`, { method: "DELETE" });
}

// ─── Config: Pipeline / Institutions / Report Layout ───

export async function getPipelineConfig(): Promise<PipelineConfigData> {
  return apiFetch("/config/pipeline");
}

export async function updatePipelineConfig(data: Partial<PipelineConfigData>): Promise<PipelineConfigData> {
  return apiFetch("/config/pipeline", { method: "PUT", body: JSON.stringify(data) });
}

export async function getInstitutionsConfig(): Promise<{ config_json: Record<string, unknown> }> {
  return apiFetch("/config/institutions");
}

export async function updateInstitutionsConfig(config_json: Record<string, unknown>): Promise<{ config_json: Record<string, unknown> }> {
  return apiFetch("/config/institutions", { method: "PUT", body: JSON.stringify({ config_json }) });
}

export async function getReportLayout(): Promise<{ config_json: Record<string, unknown> }> {
  return apiFetch("/config/report-layout");
}

export async function updateReportLayout(config_json: Record<string, unknown>): Promise<{ config_json: Record<string, unknown> }> {
  return apiFetch("/config/report-layout", { method: "PUT", body: JSON.stringify({ config_json }) });
}

// ─── Config: Import / Export ───

export async function importConfig(data: Partial<ConfigExport>): Promise<{ imported: string[]; total: number }> {
  return apiFetch("/config/import", { method: "POST", body: JSON.stringify(data) });
}

export async function exportConfig(): Promise<ConfigExport> {
  return apiFetch("/config/export");
}

// ─── Transaction Types ───

export interface TransactionItem {
  data: string;
  descricao: string;
  valor: number;
  banco: string;
  categoria: string;
  origem?: string;
  tipo_conta: string;
  titular: string;
  moeda: string;
  transaction_hash: string;
  is_overridden: boolean;
}

export interface TransactionSummary {
  total_receitas: number;
  total_despesas: number;
  saldo: number;
  count: number;
  periodo_inicio: string | null;
  periodo_fim: string | null;
}

export interface TransactionListResponse {
  transactions: TransactionItem[];
  total: number;
  page: number;
  page_size: number;
  summary: TransactionSummary;
}

export interface TransactionOverrideResponse {
  id: string;
  transaction_hash: string;
  original_category: string;
  new_category: string;
  notes: string | null;
  reviewed: boolean;
  created_at: string;
}

// ─── Dashboard Types ───

export interface DashboardKPI {
  label: string;
  value: string;
  raw_value: number;
  delta?: number | null;
  delta_percent?: number | null;
}

export interface DashboardChart {
  chart_type: string;
  title: string;
  data: Record<string, unknown>;
}

export interface DashboardAlert {
  severity: string;
  title: string;
  message: string;
}

export interface DashboardResponse {
  kpis: DashboardKPI[];
  charts: DashboardChart[];
  alerts: DashboardAlert[];
  data_freshness: string | null;
  periodo: string | null;
}

// ─── Notification Types ───

export interface NotificationItem {
  id: string;
  severity: string;
  title: string;
  message: string;
  source: string | null;
  is_read: boolean;
  created_at: string;
}

export interface NotificationListResponse {
  notifications: NotificationItem[];
  total: number;
  unread_count: number;
}

// ─── Transaction API ───

export async function listTransactions(params?: {
  member?: string;
  bank?: string;
  category?: string;
  date_from?: string;
  date_to?: string;
  value_min?: number;
  value_max?: number;
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<TransactionListResponse> {
  const qp = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qp.set(k, String(v));
    });
  }
  const qs = qp.toString();
  return apiFetch(`/transactions${qs ? `?${qs}` : ""}`);
}

export async function overrideTransactionCategory(
  hash: string,
  data: { new_category: string; notes?: string }
): Promise<TransactionOverrideResponse> {
  return apiFetch(`/transactions/${hash}/override`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function removeTransactionOverride(hash: string): Promise<void> {
  return apiFetch(`/transactions/${hash}/override`, { method: "DELETE" });
}

// ─── Dashboard API ───

export async function getDashboard(): Promise<DashboardResponse> {
  return apiFetch("/dashboard");
}

// ─── Notification API ───

export async function listNotifications(params?: {
  severity?: string;
  is_read?: boolean;
  limit?: number;
}): Promise<NotificationListResponse> {
  const qp = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) qp.set(k, String(v));
    });
  }
  const qs = qp.toString();
  return apiFetch(`/notifications${qs ? `?${qs}` : ""}`);
}

export async function markNotificationsRead(ids: string[]): Promise<void> {
  return apiFetch("/notifications/read", {
    method: "PATCH",
    body: JSON.stringify({ notification_ids: ids }),
  });
}

export async function deleteNotification(id: string): Promise<void> {
  return apiFetch(`/notifications/${id}`, { method: "DELETE" });
}

// ─── LLM Config Types ───

export interface LLMConfigResponse {
  id: string;
  provider: string;
  model_name: string;
  max_tokens: number;
  temperature: number;
  created_at: string;
  updated_at: string;
}

export interface LLMTierResponse {
  tier: string;
  has_llm_config: boolean;
}

export async function getLLMConfig(): Promise<LLMConfigResponse | null> {
  return apiFetch("/config/llm");
}

export async function saveLLMConfig(data: {
  provider: string;
  api_key: string;
  model_name: string;
  max_tokens?: number;
  temperature?: number;
}): Promise<LLMConfigResponse> {
  return apiFetch("/config/llm", { method: "PUT", body: JSON.stringify(data) });
}

export async function deleteLLMConfig(): Promise<void> {
  return apiFetch("/config/llm", { method: "DELETE" });
}

export async function testLLMConnection(): Promise<{ success: boolean; message: string; model?: string }> {
  return apiFetch("/config/llm/test", { method: "POST" });
}

export async function getLLMTier(): Promise<LLMTierResponse> {
  return apiFetch("/config/llm/tier");
}

// ─── Pipeline Resume ───

export async function resumePipelineRun(runId: string): Promise<void> {
  return apiFetch(`/pipeline/runs/${runId}/resume`, { method: "POST" });
}

export async function listStageReviews(runId: string): Promise<unknown[]> {
  return apiFetch(`/pipeline/runs/${runId}/reviews`);
}

export async function submitStageReview(
  runId: string,
  reviewId: string,
  data: { action: string; edited_output?: Record<string, unknown>; notes?: string }
): Promise<unknown> {
  return apiFetch(`/pipeline/runs/${runId}/reviews/${reviewId}`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ═══════════════════════════════════════════════════════════════════════
// Workspaces (F8) — listagem de memberships do usuário
// ═══════════════════════════════════════════════════════════════════════

export interface UserWorkspace {
  id: string;
  name: string;
  family_surname: string | null;
  role: "owner" | "member";
  joined_at: string;
}

export interface UserWorkspaceList {
  workspaces: UserWorkspace[];
  total: number;
}

export async function listMyWorkspaces(): Promise<UserWorkspaceList> {
  return apiFetch("/me/workspaces");
}

// ═══════════════════════════════════════════════════════════════════════
// Goals — Meta IF (ADR-073, F8.1)
// Padrão F8+: endpoints escopados por /api/workspaces/{ws_id}/...
// ═══════════════════════════════════════════════════════════════════════

export interface IFGoalInputs {
  renda_passiva_mensal_brl: number;
  trs_pct: number;
  retorno_real_anual_pct: number;
  horizonte_anos: number;
  taxa_retirada_conservadora_pct?: number;
}

export interface IFGoalDerived {
  if_meta_brl: number;
  aporte_necessario_mensal_brl: number;
  if_meta_conservadora_brl: number;
}

export interface IFGoalResponse {
  id: string;
  workspace_id: string;
  type: "INDEPENDENCIA_FINANCEIRA";
  inputs: IFGoalInputs;
  derived: IFGoalDerived;
  effective_from: string;
  effective_to: string | null;
  is_template: boolean;
  notes: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface IFGoalHistoryResponse {
  goals: IFGoalResponse[];
  total: number;
}

export interface IFGoalComputeRequest {
  inputs: IFGoalInputs;
  patrimonio_atual_brl?: number;
}

export interface IFGoalComputeResponse {
  derived: IFGoalDerived;
  percentual_conquistado: number | null;
  faltante_brl: number | null;
}

export async function computeIFGoal(
  workspaceId: string,
  body: IFGoalComputeRequest
): Promise<IFGoalComputeResponse> {
  return apiFetch(`/workspaces/${workspaceId}/goals/if/compute`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getIFGoal(
  workspaceId: string
): Promise<IFGoalResponse> {
  return apiFetch(`/workspaces/${workspaceId}/goals/if`);
}

export async function getIFGoalHistory(
  workspaceId: string
): Promise<IFGoalHistoryResponse> {
  return apiFetch(`/workspaces/${workspaceId}/goals/if/history`);
}

export async function upsertIFGoal(
  workspaceId: string,
  inputs: IFGoalInputs,
  notes?: string
): Promise<IFGoalResponse> {
  return apiFetch(`/workspaces/${workspaceId}/goals/if`, {
    method: "PUT",
    body: JSON.stringify({ inputs, notes }),
  });
}
