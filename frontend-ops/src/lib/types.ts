// Espelho TypeScript dos DTOs de backend/app/schemas/admin.py (ADR-116).
// Mantenha em sincronia manual enquanto codegen OpenAPI não cobrir /admin/*.
// Fonte de verdade: docs/api/v1/openapi.json + backend/app/schemas/admin.py.

export type AdminRole = "superadmin" | "ops" | string;

export interface AdminPrincipal {
  username: string;
  role: AdminRole;
}

export interface AdminLoginResponse extends AdminPrincipal {
  expires_in_minutes: number;
}

export interface AdminUserSummary {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_developer: boolean;
  created_at: string;
}

export interface AdminUserListResponse {
  users: AdminUserSummary[];
  total: number;
}

export interface AnonymizeUserResponse {
  user_id: string;
  anonymized_email: string;
}

export interface HardDeleteUserResponse {
  user_id: string;
}

export interface ResetPasswordResponse {
  user_id: string;
  temp_password: string;
}

export interface SetDeveloperFlagResponse {
  user_id: string;
  is_developer: boolean;
  changed: boolean;
}

export interface UpdateUserEmailResponse {
  user_id: string;
  email: string;
  changed: boolean;
}

export interface UpdateUserProfileResponse {
  user_id: string;
  changed: boolean;
  fields: string[];
}

export interface PurgeDocumentsResponse {
  preview: boolean;
  count: number;
  ids: string[];
  blobs_removed: number | null;
}

export interface DeleteDocumentResponse {
  document_id: string;
  blob_removed: boolean;
}

export interface MetricsResponse {
  users_total: number;
  users_active: number;
  workspaces_total: number;
  documents_total: number;
  documents_needs_review: number;
  storage_bytes_total: number;
  pipeline_runs_total: number;
  pipeline_runs_last_period: number;
  period_days: number;
  generated_at: string;
}

export interface ReportSummary {
  id: string;
  workspace_id: string;
  title: string;
  period: string | null;
  created_at: string;
  size_bytes: number | null;
}

export interface AdminReportListResponse {
  reports: ReportSummary[];
}

export interface AdminErrorResponse {
  detail: string;
}
