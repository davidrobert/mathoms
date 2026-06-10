import { API_BASE, apiFetch, clearToken } from "./core";

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
  is_developer: boolean;
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

/** Logout best-effort (ADR-170): revoga a família de refresh no backend
 * (cookie httpOnly viaja sozinho) e limpa o access token local. */
export async function logout(): Promise<void> {
  try {
    await fetch(`${API_BASE}/auth/logout`, { method: "POST" });
  } catch {
    // best-effort — sessão local é limpa de qualquer forma
  }
  clearToken();
}
