const API_BASE = "/api";

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

export interface ReportResponse {
  id: string;
  workspace_id: string;
  title: string;
  period: string | null;
  size_bytes: number | null;
  created_at: string;
}

export interface ReportListResponse {
  reports: ReportResponse[];
  total: number;
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("fin_token");
}

export function setToken(token: string) {
  localStorage.setItem("fin_token", token);
}

export function clearToken() {
  localStorage.removeItem("fin_token");
}

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string
  ) {
    super(detail);
  }
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

export async function getMe(): Promise<UserResponse> {
  return apiFetch("/auth/me");
}

export async function listReports(): Promise<ReportListResponse> {
  return apiFetch("/reports");
}

export function getReportHtmlUrl(reportId: string): string {
  return `${API_BASE}/reports/${reportId}/html`;
}
