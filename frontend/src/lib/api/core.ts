// A6e.5 · ADR-108 — prefix canônico. Alias /api/* continua funcional no
// backend até F7A (LegacyApiDeprecationMiddleware anuncia Deprecation).
export const API_BASE = "/api/v1";

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

export async function apiFetch<T>(
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
