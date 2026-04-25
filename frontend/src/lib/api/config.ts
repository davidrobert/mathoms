import { apiFetch } from "./core";

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

export async function getWorkspaceSettings(workspaceId: string): Promise<WorkspaceSettings> {
  return apiFetch(`/workspaces/${workspaceId}/config/workspace`);
}

export async function updateWorkspaceSettings(
  workspaceId: string,
  data: Partial<Pick<WorkspaceSettings, "family_surname">>,
): Promise<WorkspaceSettings> {
  return apiFetch(`/workspaces/${workspaceId}/config/workspace`, { method: "PATCH", body: JSON.stringify(data) });
}

// ─── Config: Members ───

export async function listMembers(workspaceId: string): Promise<{ members: FamilyMemberConfig[]; total: number }> {
  return apiFetch(`/workspaces/${workspaceId}/config/members`);
}

// `Omit<T, "id" | "accounts">` preserva `key: string` (required) do
// FamilyMemberConfig. Intersection com `{ key?: string }` NÃO sobrescreve
// — TypeScript mantém o tipo mais restrito. Por isso omitimos `key`
// explicitamente antes de re-declará-lo como opcional.
export type CreateMemberPayload = Omit<
  FamilyMemberConfig,
  "id" | "accounts" | "key"
> & {
  /** Se omitido, o backend gera um identificador único a partir do nome completo */
  key?: string;
};

export async function createMember(workspaceId: string, data: CreateMemberPayload): Promise<FamilyMemberConfig> {
  return apiFetch(`/workspaces/${workspaceId}/config/members`, { method: "POST", body: JSON.stringify(data) });
}

export async function updateMember(workspaceId: string, id: string, data: Partial<FamilyMemberConfig>): Promise<FamilyMemberConfig> {
  return apiFetch(`/workspaces/${workspaceId}/config/members/${id}`, { method: "PUT", body: JSON.stringify(data) });
}

export async function deleteMember(workspaceId: string, id: string): Promise<void> {
  return apiFetch(`/workspaces/${workspaceId}/config/members/${id}`, { method: "DELETE" });
}

// ─── Config: Bank Accounts ───

export async function createBankAccount(workspaceId: string, memberId: string, data: Omit<BankAccountConfig, "id">): Promise<BankAccountConfig> {
  return apiFetch(`/workspaces/${workspaceId}/config/members/${memberId}/accounts`, { method: "POST", body: JSON.stringify(data) });
}

export async function deleteBankAccount(workspaceId: string, memberId: string, accountId: string): Promise<void> {
  return apiFetch(`/workspaces/${workspaceId}/config/members/${memberId}/accounts/${accountId}`, { method: "DELETE" });
}

// ─── Config: Categories ───

export async function listCategories(workspaceId: string): Promise<{ categories: CategoryConfig[]; total: number }> {
  return apiFetch(`/workspaces/${workspaceId}/config/categories`);
}

export async function createCategory(workspaceId: string, data: Omit<CategoryConfig, "id">): Promise<CategoryConfig> {
  return apiFetch(`/workspaces/${workspaceId}/config/categories`, { method: "POST", body: JSON.stringify(data) });
}

export async function updateCategory(workspaceId: string, id: string, data: Partial<CategoryConfig>): Promise<CategoryConfig> {
  return apiFetch(`/workspaces/${workspaceId}/config/categories/${id}`, { method: "PUT", body: JSON.stringify(data) });
}

export async function deleteCategory(workspaceId: string, id: string): Promise<void> {
  return apiFetch(`/workspaces/${workspaceId}/config/categories/${id}`, { method: "DELETE" });
}

// ─── Config: Pipeline / Institutions / Report Layout ───

export async function getPipelineConfig(workspaceId: string): Promise<PipelineConfigData> {
  return apiFetch(`/workspaces/${workspaceId}/config/pipeline`);
}

export async function updatePipelineConfig(workspaceId: string, data: Partial<PipelineConfigData>): Promise<PipelineConfigData> {
  return apiFetch(`/workspaces/${workspaceId}/config/pipeline`, { method: "PUT", body: JSON.stringify(data) });
}

export async function getInstitutionsConfig(workspaceId: string): Promise<{ config_json: Record<string, unknown> }> {
  return apiFetch(`/workspaces/${workspaceId}/config/institutions`);
}

export async function updateInstitutionsConfig(workspaceId: string, config_json: Record<string, unknown>): Promise<{ config_json: Record<string, unknown> }> {
  return apiFetch(`/workspaces/${workspaceId}/config/institutions`, { method: "PUT", body: JSON.stringify({ config_json }) });
}

export async function getReportLayout(workspaceId: string): Promise<{ config_json: Record<string, unknown> }> {
  return apiFetch(`/workspaces/${workspaceId}/config/report-layout`);
}

export async function updateReportLayout(workspaceId: string, config_json: Record<string, unknown>): Promise<{ config_json: Record<string, unknown> }> {
  return apiFetch(`/workspaces/${workspaceId}/config/report-layout`, { method: "PUT", body: JSON.stringify({ config_json }) });
}

// ─── Config: Import / Export ───

export async function importConfig(workspaceId: string, data: Partial<ConfigExport>): Promise<{ imported: string[]; total: number }> {
  return apiFetch(`/workspaces/${workspaceId}/config/import`, { method: "POST", body: JSON.stringify(data) });
}

export async function exportConfig(workspaceId: string): Promise<ConfigExport> {
  return apiFetch(`/workspaces/${workspaceId}/config/export`);
}

// ─── LLM Config Types ───

export interface LLMConfigResponse {
  id: string;
  provider: string;
  api_key_masked: string;
  api_key_status: "valid" | "invalid";
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

export async function getLLMConfig(workspaceId: string): Promise<LLMConfigResponse | null> {
  return apiFetch(`/workspaces/${workspaceId}/config/llm`);
}

export async function saveLLMConfig(workspaceId: string, data: {
  provider: string;
  api_key: string;
  model_name: string;
  max_tokens?: number;
  temperature?: number;
}): Promise<LLMConfigResponse> {
  return apiFetch(`/workspaces/${workspaceId}/config/llm`, { method: "PUT", body: JSON.stringify(data) });
}

export async function deleteLLMConfig(workspaceId: string): Promise<void> {
  return apiFetch(`/workspaces/${workspaceId}/config/llm`, { method: "DELETE" });
}

export async function testLLMConnection(workspaceId: string): Promise<{ success: boolean; message: string; model?: string }> {
  return apiFetch(`/workspaces/${workspaceId}/config/llm/test`, { method: "POST" });
}

export async function getLLMTier(workspaceId: string): Promise<LLMTierResponse> {
  return apiFetch(`/workspaces/${workspaceId}/config/llm/tier`);
}
