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
  classification_confidence?: number | null;
  needs_review?: boolean;
  possible_duplicate_of_id?: string | null;
  file_size_bytes: number | null;
  content_type: string | null;
  error_message: string | null;
  uploaded_at: string;
  pipeline_last_run_at?: string | null;
  pipeline_e2_extract_ok?: boolean | null;
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
  incremental: boolean;
  celery_task_id: string | null;
  started_at: string;
  completed_at: string | null;
  stage_logs: PipelineStageLog[];
}

export interface PipelineRunListResponse {
  runs: PipelineRunResponse[];
  total: number;
}

/** Live sub-step within a stage (WebSocket ``stage_activity``). */
export interface PipelineStageActivity {
  stage: string;
  file?: string;
  message?: string;
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

/** Detail estruturado retornado pelo backend em erros 4xx de F9+
 * (`{code, message}`). Para erros antigos, vira string direta. */
export type ApiErrorDetail = string | { code?: string; message?: string };

export class ApiError extends Error {
  /** Detail cru. Pode ser string (legado) ou `{code, message}` (F9+).
   * Para extrair o code: `getErrorCode(err)`. */
  public readonly detailRaw: ApiErrorDetail;

  constructor(public status: number, detail: ApiErrorDetail) {
    const msg =
      typeof detail === "string"
        ? detail
        : detail?.message ?? `HTTP ${status}`;
    super(msg);
    this.detailRaw = detail;
  }

  /** Accessor de compat com consumidores antigos que esperam string. */
  get detail(): string {
    return typeof this.detailRaw === "string"
      ? this.detailRaw
      : this.detailRaw?.message ?? `HTTP ${this.status}`;
  }
}

/** Extrai `code` de um ApiError F9+. Retorna undefined se detail é string. */
export function getErrorCode(err: unknown): string | undefined {
  if (!(err instanceof ApiError)) return undefined;
  const d = err.detailRaw;
  return typeof d === "object" && d ? d.code : undefined;
}

// ─── Fetch Helpers ───

/** Hook global disparado quando backend retorna `token_revoked`.
 * Instalado por `AuthBootstrap` no root layout — quando dispara, força
 * logout + redirect para login. Exportado para testes. */
let onTokenRevoked: (() => void) | null = null;
export function setTokenRevokedHandler(handler: (() => void) | null) {
  onTokenRevoked = handler;
}

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
    const detail: ApiErrorDetail = body.detail ?? `HTTP ${res.status}`;

    // F9.2 · forced logout — detecta token_revoked e limpa sessão.
    if (
      res.status === 401 &&
      typeof detail === "object" &&
      detail?.code === "token_revoked"
    ) {
      clearToken();
      if (onTokenRevoked) onTokenRevoked();
    }

    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// ─── Auth ───

export async function getMe(): Promise<UserResponse> {
  return apiFetch("/auth/me");
}

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

/** F9 · F1.5 — URL de download do HTML standalone (E6). Preservado como
 *  produto para compartilhamento offline (contador, anexo, backup). */
export function getReportDownloadHtmlUrl(reportId: string): string {
  return `${API_BASE}/reports/${reportId}/download.html`;
}

/** F9 · F4.2 — URL de download do PDF server-side (Playwright). */
export function getReportDownloadPdfUrl(reportId: string): string {
  return `${API_BASE}/reports/${reportId}/download.pdf`;
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
  incremental?: boolean;
}): Promise<PipelineRunResponse> {
  return apiFetch("/pipeline/run", {
    method: "POST",
    body: JSON.stringify({
      from_stage: opts?.from_stage ?? null,
      skip_llm: opts?.skip_llm ?? true,
      stop_on_error: opts?.stop_on_error ?? true,
      incremental: opts?.incremental ?? false,
    }),
  });
}

export async function getNewDocCount(): Promise<{ new_count: number }> {
  return apiFetch("/pipeline/new-doc-count");
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
  /** Nome civil anterior / de nascimento (contas antigas); opcional */
  birth_name?: string | null;
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

export type CreateMemberPayload = Omit<FamilyMemberConfig, "id" | "accounts"> & {
  /** Se omitido, o backend gera um identificador único a partir do nome completo */
  key?: string;
};

export async function createMember(data: CreateMemberPayload): Promise<FamilyMemberConfig> {
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

/** Papel do usuário em um workspace.
 * UI labels (pt-BR) definidos em `frontend/src/lib/roleLabels.ts`:
 *   owner  → "Responsável"
 *   member → "Coadministrador"
 *   viewer → "Acompanha"
 */
export type WorkspaceRole = "owner" | "member" | "viewer";

/** Papéis que podem ser atribuídos via convite (owner nunca é convidável). */
export type InvitableRole = "member" | "viewer";

export interface UserWorkspace {
  id: string;
  name: string;
  family_surname: string | null;
  role: WorkspaceRole;
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
// Members & Invitations (F9 — workspace sharing)
// ═══════════════════════════════════════════════════════════════════════

export interface WorkspaceMemberResponse {
  user_id: string;
  email: string;
  full_name: string;
  role: WorkspaceRole;
  joined_at: string;
  invited_by: string | null;
}

export interface WorkspaceMemberList {
  members: WorkspaceMemberResponse[];
  total: number;
}

export type InvitationStatus = "pending" | "accepted" | "revoked" | "expired";

export interface InvitationResponse {
  id: string;
  workspace_id: string;
  email: string;
  role: WorkspaceRole;
  status: InvitationStatus;
  invited_by: string | null;
  expires_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
  created_at: string;
}

export interface InvitationCreateResponse {
  invitation: InvitationResponse;
  /** Token cru — exposto apenas uma vez. Copie o `invite_path` ou monte a
   * URL absoluta com `window.location.origin + invite_path` pra
   * enviar ao convidado. */
  token: string;
  invite_path: string;
}

export interface InvitationListResponse {
  invitations: InvitationResponse[];
  total: number;
}

export interface InvitationPreviewResponse {
  workspace_name: string;
  workspace_family_surname: string | null;
  role: WorkspaceRole;
  invited_by_name: string | null;
  invited_by_email: string | null;
  email: string;
  expires_at: string;
  status: InvitationStatus;
}

export interface InvitationAcceptResponse {
  workspace_id: string;
  role: WorkspaceRole;
  joined_at: string;
}

export async function listWorkspaceMembers(
  workspaceId: string
): Promise<WorkspaceMemberList> {
  return apiFetch(`/workspaces/${workspaceId}/members`);
}

export async function updateMemberRole(
  workspaceId: string,
  userId: string,
  role: InvitableRole
): Promise<WorkspaceMemberResponse> {
  return apiFetch(`/workspaces/${workspaceId}/members/${userId}`, {
    method: "PATCH",
    body: JSON.stringify({ role }),
  });
}

export async function removeWorkspaceMember(
  workspaceId: string,
  userId: string
): Promise<void> {
  return apiFetch(`/workspaces/${workspaceId}/members/${userId}`, {
    method: "DELETE",
  });
}

export async function listWorkspaceInvitations(
  workspaceId: string,
  opts: { onlyPending?: boolean } = {}
): Promise<InvitationListResponse> {
  const qs = opts.onlyPending ? "?only_pending=true" : "";
  return apiFetch(`/workspaces/${workspaceId}/invitations${qs}`);
}

export async function createWorkspaceInvitation(
  workspaceId: string,
  email: string,
  role: InvitableRole
): Promise<InvitationCreateResponse> {
  return apiFetch(`/workspaces/${workspaceId}/invitations`, {
    method: "POST",
    body: JSON.stringify({ email, role }),
  });
}

export async function revokeWorkspaceInvitation(
  workspaceId: string,
  invitationId: string
): Promise<void> {
  return apiFetch(`/workspaces/${workspaceId}/invitations/${invitationId}`, {
    method: "DELETE",
  });
}

/** Rota pública — não envia token de auth. */
export async function previewInvitation(
  token: string
): Promise<InvitationPreviewResponse> {
  const res = await fetch(`${API_BASE}/invitations/${token}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/** Precisa de auth (user logado). */
export async function acceptInvitation(
  token: string
): Promise<InvitationAcceptResponse> {
  return apiFetch(`/invitations/${token}/accept`, { method: "POST" });
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
  /** Aporte assumindo patrimônio inicial zero (baseline; persistido). */
  aporte_necessario_mensal_brl: number;
  if_meta_conservadora_brl: number;
  /** Quando há patrimônio de referência (ex.: último relatório), aporte para fechar o gap. */
  aporte_mensal_com_patrimonio_atual_brl?: number | null;
  patrimonio_atual_utilizado_brl?: number | null;
}

/** Aporte a exibir: ajustado ao patrimônio conhecido, senão baseline. */
export function ifMonthlyContributionDisplay(d: IFGoalDerived): number {
  return (
    d.aporte_mensal_com_patrimonio_atual_brl ?? d.aporte_necessario_mensal_brl
  );
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
  /** F9 · nome humano do autor (join com users.full_name). */
  created_by_name: string | null;
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

// ═══════════════════════════════════════════════════════════════════════
// Tasks (ADR-074, F8.2)
// ═══════════════════════════════════════════════════════════════════════

export type TaskPriority = "S" | "R" | "O";
export type TaskStatus =
  | "pending"
  | "in_progress"
  | "done"
  | "cancelled"
  | "blocked";
export type TaskDeadlineKind =
  | "HARD_DATE"
  | "MONTH"
  | "QUARTER"
  | "CONDITIONAL"
  | "UNSCHEDULED";
export type TaskCreatedFrom = "manual" | "seed" | "llm_suggestion";

export interface TaskResponse {
  id: string;
  workspace_id: string;
  number: number;
  title: string;
  description: string | null;
  category: string;
  priority: TaskPriority;
  status: TaskStatus;
  status_reason: string | null;
  deadline_kind: TaskDeadlineKind;
  deadline_date: string | null;
  deadline_label: string | null;
  ref: string | null;
  parent_task_id: string | null;
  related_transaction_id: string | null;
  related_goal_id: string | null;
  assigned_to: string | null;
  created_from: TaskCreatedFrom;
  source_suggestion_id: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskListResponse {
  tasks: TaskResponse[];
  total: number;
}

export interface TaskCreateBody {
  title: string;
  description?: string | null;
  category: string;
  priority: TaskPriority;
  deadline_kind?: TaskDeadlineKind;
  deadline_date?: string | null;
  deadline_label?: string | null;
  ref?: string | null;
  parent_task_id?: string | null;
  related_goal_id?: string | null;
  assigned_to?: string | null;
  number?: number;
}

export interface TaskUpdateBody {
  title?: string;
  description?: string | null;
  category?: string;
  priority?: TaskPriority;
  deadline_kind?: TaskDeadlineKind;
  deadline_date?: string | null;
  deadline_label?: string | null;
  ref?: string | null;
  parent_task_id?: string | null;
  related_goal_id?: string | null;
  assigned_to?: string | null;
}

export interface TaskFiltersQuery {
  status_filter?: TaskStatus;
  priority?: TaskPriority;
  category?: string;
  deadline_before?: string;
  deadline_after?: string;
  assigned_to?: string;
  include_done?: boolean;
  include_cancelled?: boolean;
}

export async function listTasks(
  workspaceId: string,
  filters: TaskFiltersQuery = {}
): Promise<TaskListResponse> {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(filters)) {
    if (v !== undefined && v !== null) params.set(k, String(v));
  }
  const qs = params.toString();
  return apiFetch(
    `/workspaces/${workspaceId}/tasks${qs ? `?${qs}` : ""}`
  );
}

export async function listUpcomingTasks(
  workspaceId: string,
  days = 7
): Promise<TaskListResponse> {
  return apiFetch(`/workspaces/${workspaceId}/tasks/upcoming?days=${days}`);
}

export async function getTask(
  workspaceId: string,
  taskId: string
): Promise<TaskResponse> {
  return apiFetch(`/workspaces/${workspaceId}/tasks/${taskId}`);
}

export async function createTask(
  workspaceId: string,
  body: TaskCreateBody
): Promise<TaskResponse> {
  return apiFetch(`/workspaces/${workspaceId}/tasks`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateTask(
  workspaceId: string,
  taskId: string,
  body: TaskUpdateBody
): Promise<TaskResponse> {
  return apiFetch(`/workspaces/${workspaceId}/tasks/${taskId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function transitionTaskStatus(
  workspaceId: string,
  taskId: string,
  status: TaskStatus,
  reason?: string
): Promise<TaskResponse> {
  return apiFetch(`/workspaces/${workspaceId}/tasks/${taskId}/status`, {
    method: "POST",
    body: JSON.stringify({ status, status_reason: reason }),
  });
}

export async function deleteTask(
  workspaceId: string,
  taskId: string
): Promise<void> {
  return apiFetch(`/workspaces/${workspaceId}/tasks/${taskId}`, {
    method: "DELETE",
  });
}

// ─── Task Suggestions ────────────────────────────────────────────────

export type SuggestionStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "merged";

export interface TaskSuggestionResponse {
  id: string;
  workspace_id: string;
  proposed_payload: {
    title: string;
    category: string;
    priority: TaskPriority;
    deadline_kind?: TaskDeadlineKind;
    deadline_date?: string | null;
    deadline_label?: string | null;
    description?: string | null;
    [key: string]: unknown;
  };
  source: "e5n_llm" | "cross_validation" | "system_rule";
  source_run_id: string | null;
  status: SuggestionStatus;
  rejection_reason: string | null;
  approved_task_id: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
}

export interface TaskSuggestionListResponse {
  suggestions: TaskSuggestionResponse[];
  total: number;
}

export async function listTaskSuggestions(
  workspaceId: string,
  statusFilter: SuggestionStatus = "pending"
): Promise<TaskSuggestionListResponse> {
  return apiFetch(
    `/workspaces/${workspaceId}/task-suggestions?status_filter=${statusFilter}`
  );
}

export async function approveTaskSuggestion(
  workspaceId: string,
  suggestionId: string,
  editedPayload?: TaskCreateBody
): Promise<TaskResponse> {
  return apiFetch(
    `/workspaces/${workspaceId}/task-suggestions/${suggestionId}/approve`,
    {
      method: "POST",
      body: JSON.stringify({ edited_payload: editedPayload }),
    }
  );
}

export async function rejectTaskSuggestion(
  workspaceId: string,
  suggestionId: string,
  reason?: string
): Promise<TaskSuggestionResponse> {
  return apiFetch(
    `/workspaces/${workspaceId}/task-suggestions/${suggestionId}/reject`,
    {
      method: "POST",
      body: JSON.stringify({ reason }),
    }
  );
}

export async function mergeTaskSuggestion(
  workspaceId: string,
  suggestionId: string,
  targetTaskId: string
): Promise<TaskSuggestionResponse> {
  return apiFetch(
    `/workspaces/${workspaceId}/task-suggestions/${suggestionId}/merge-into/${targetTaskId}`,
    { method: "POST" }
  );
}

export interface ScanDeadlinesResult {
  created: number;
  skipped_existing: number;
  evaluated: number;
}

export async function scanTaskDeadlines(
  workspaceId: string
): Promise<ScanDeadlinesResult> {
  return apiFetch(`/workspaces/${workspaceId}/tasks/scan-deadlines`, {
    method: "POST",
  });
}

// ─── Task Progress (F8.3 — Task↔Transaction) ────────────────────────

export interface TaskProgress {
  is_trackable: boolean;
  period_start: string | null;
  period_end: string | null;
  target_brl: number | null;
  executed_brl: number | null;
  percent_executed: number | null;
  matched_keywords: string[];
  matched_transactions_count: number;
}

export async function getTaskProgress(
  workspaceId: string,
  taskId: string
): Promise<TaskProgress> {
  return apiFetch(`/workspaces/${workspaceId}/tasks/${taskId}/progress`);
}

// ─── Task↔Goal (F8.3) ──────────────────────────────────────────────

export async function listTasksForGoal(
  workspaceId: string,
  goalId: string,
  includeDone = false
): Promise<TaskListResponse> {
  const qs = new URLSearchParams();
  if (includeDone) qs.set("include_done", "true");
  return apiFetch(
    `/workspaces/${workspaceId}/goals/${goalId}/tasks${
      qs.toString() ? `?${qs}` : ""
    }`
  );
}

// ─── Report Tasks Snapshot (ADR-074 §F8.3) ────────────────────────

export interface ReportTasksSnapshot {
  is_live_fallback: boolean;
  version: number;
  captured_at: string | null;
  total: number;
  counts_by_status: Record<string, number>;
  counts_by_priority: Record<string, number>;
  tasks: Array<{
    id?: string;
    number: number;
    title: string;
    description?: string | null;
    category: string;
    priority: TaskPriority;
    status: TaskStatus;
    ref: string | null;
    deadline_kind: TaskDeadlineKind;
    deadline_date: string | null;
    deadline_label: string | null;
  }>;
}

export async function getReportTasks(
  reportId: string
): Promise<ReportTasksSnapshot> {
  return apiFetch(`/reports/${reportId}/tasks`);
}

// ─── Task Attachments (F8.3) ──────────────────────────────────────────

export interface TaskAttachmentMeta {
  id: string;
  task_id: string;
  workspace_id: string;
  original_filename: string;
  content_type: string | null;
  size_bytes: number | null;
  uploaded_by: string | null;
  created_at: string;
}

export interface TaskAttachmentList {
  attachments: TaskAttachmentMeta[];
  total: number;
}

export async function listTaskAttachments(
  workspaceId: string,
  taskId: string
): Promise<TaskAttachmentList> {
  return apiFetch(`/workspaces/${workspaceId}/tasks/${taskId}/attachments`);
}

export async function uploadTaskAttachment(
  workspaceId: string,
  taskId: string,
  file: File
): Promise<TaskAttachmentMeta> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch(
    `/workspaces/${workspaceId}/tasks/${taskId}/attachments`,
    { method: "POST", body: form }
  );
}

export async function deleteTaskAttachment(
  workspaceId: string,
  taskId: string,
  attachmentId: string
): Promise<void> {
  return apiFetch(
    `/workspaces/${workspaceId}/tasks/${taskId}/attachments/${attachmentId}`,
    { method: "DELETE" }
  );
}

export function taskAttachmentDownloadUrl(
  workspaceId: string,
  taskId: string,
  attachmentId: string
): string {
  return `${API_BASE}/workspaces/${workspaceId}/tasks/${taskId}/attachments/${attachmentId}/download`;
}

// ─── Feature Flags (F8.3) ────────────────────────────────────────────

export interface FeatureFlagsResponse {
  flags: Record<string, boolean>;
}

export async function getFeatureFlags(
  workspaceId: string
): Promise<FeatureFlagsResponse> {
  return apiFetch(`/workspaces/${workspaceId}/feature-flags`);
}

export async function setFeatureFlag(
  workspaceId: string,
  flag: string,
  enabled: boolean
): Promise<FeatureFlagsResponse> {
  return apiFetch(`/workspaces/${workspaceId}/feature-flags/${flag}`, {
    method: "PUT",
    body: JSON.stringify({ enabled }),
  });
}
