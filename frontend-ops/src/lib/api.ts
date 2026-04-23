// Client HTTP tipado para /admin/*. Todas as chamadas passam por rewrites() do
// Next (server-side → backend FastAPI), então o browser usa sempre same-origin
// e o cookie ops_session flui naturalmente via HttpOnly + Path=/admin.

import type {
  AdminLoginResponse,
  AdminPrincipal,
  AdminReportListResponse,
  AdminUserListResponse,
  AnonymizeUserResponse,
  DeleteDocumentResponse,
  HardDeleteUserResponse,
  MetricsResponse,
  PurgeDocumentsResponse,
  ResetPasswordResponse,
  SetDeveloperFlagResponse,
  UpdateUserEmailResponse,
  UpdateUserProfileResponse,
} from "./types";

export class AdminApiError extends Error {
  readonly status: number;
  readonly code: string;
  constructor(status: number, code: string) {
    super(`${status}:${code}`);
    this.status = status;
    this.code = code;
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const res = await fetch(`/admin${path}`, {
    method: opts.method ?? "GET",
    headers: opts.body ? { "Content-Type": "application/json" } : undefined,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
    credentials: "include",
    cache: "no-store",
    signal: opts.signal,
  });
  if (!res.ok) {
    const detail = await extractError(res);
    throw new AdminApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

async function extractError(res: Response): Promise<string> {
  try {
    const data = (await res.json()) as { detail?: unknown };
    if (typeof data.detail === "string") return data.detail;
    return JSON.stringify(data.detail ?? "error");
  } catch {
    return res.statusText || "error";
  }
}

export const api = {
  login: (username: string, password: string) =>
    request<AdminLoginResponse>("/login", {
      method: "POST",
      body: { username, password },
    }),

  logout: () => request<{ ok: boolean }>("/logout", { method: "POST" }),

  me: () => request<AdminPrincipal>("/me"),

  listUsers: (query: { q?: string; limit?: number } = {}) => {
    const params = new URLSearchParams();
    if (query.q) params.set("q", query.q);
    if (query.limit != null) params.set("limit", String(query.limit));
    const qs = params.toString();
    return request<AdminUserListResponse>(`/users${qs ? `?${qs}` : ""}`);
  },

  anonymizeUser: (userId: string) =>
    request<AnonymizeUserResponse>(`/users/${encodeURIComponent(userId)}/anonymize`, {
      method: "POST",
      body: { confirm: "delete" },
    }),

  hardDeleteUser: (userId: string, reason: string) =>
    request<HardDeleteUserResponse>(`/users/${encodeURIComponent(userId)}/hard-delete`, {
      method: "POST",
      body: { reason, confirm: "hard_delete" },
    }),

  resetPassword: (userId: string, newPassword?: string) =>
    request<ResetPasswordResponse>(`/users/${encodeURIComponent(userId)}/reset-password`, {
      method: "POST",
      body: newPassword ? { new_password: newPassword } : {},
    }),

  setDeveloperFlag: (userId: string, enabled: boolean) =>
    request<SetDeveloperFlagResponse>(`/users/${encodeURIComponent(userId)}/developer-flag`, {
      method: "POST",
      body: { enabled },
    }),

  updateUserEmail: (userId: string, newEmail: string) =>
    request<UpdateUserEmailResponse>(`/users/${encodeURIComponent(userId)}/email`, {
      method: "PATCH",
      body: { new_email: newEmail },
    }),

  updateUserProfile: (
    userId: string,
    patch: { full_name?: string; is_active?: boolean },
  ) =>
    request<UpdateUserProfileResponse>(`/users/${encodeURIComponent(userId)}/profile`, {
      method: "PATCH",
      body: patch,
    }),

  purgeDocuments: (scope: {
    user_id?: string;
    workspace_id?: string;
    preview: boolean;
  }) =>
    request<PurgeDocumentsResponse>("/documents/purge", {
      method: "POST",
      body: scope,
    }),

  deleteDocument: (documentId: string) =>
    request<DeleteDocumentResponse>(`/documents/${encodeURIComponent(documentId)}`, {
      method: "DELETE",
    }),

  getMetrics: (periodDays = 30) =>
    request<MetricsResponse>(`/metrics?period_days=${periodDays}`),

  listReports: (
    query: {
      user_id?: string;
      workspace_id?: string;
      limit?: number;
      offset?: number;
    } = {},
  ) => {
    const params = new URLSearchParams();
    if (query.user_id) params.set("user_id", query.user_id);
    if (query.workspace_id) params.set("workspace_id", query.workspace_id);
    if (query.limit != null) params.set("limit", String(query.limit));
    if (query.offset != null) params.set("offset", String(query.offset));
    const qs = params.toString();
    return request<AdminReportListResponse>(`/reports${qs ? `?${qs}` : ""}`);
  },
};
