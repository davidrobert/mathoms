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

/** Detail estruturado retornado pelo backend em erros 4xx.
 * - string: erros legados
 * - `{code, message}`: erros de domínio F9+
 * - array de `{loc, msg}`: validação Pydantic (FastAPI/422) */
export type PydanticValidationItem = {
  loc?: (string | number)[];
  msg?: string;
  type?: string;
};
export type ApiErrorDetail =
  | string
  | { code?: string; message?: string }
  | PydanticValidationItem[];

function formatDetail(detail: ApiErrorDetail, status: number): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const msgs = detail
      .map((d) => {
        const field = d.loc?.filter((p) => p !== "body").join(".") ?? "";
        return field ? `${field}: ${d.msg}` : d.msg;
      })
      .filter(Boolean);
    return msgs.length ? msgs.join("; ") : `HTTP ${status}`;
  }
  return detail?.message ?? `HTTP ${status}`;
}

export class ApiError extends Error {
  /** Detail cru. Pode ser string, `{code, message}` ou array Pydantic.
   * Para extrair o code: `getErrorCode(err)`. */
  public readonly detailRaw: ApiErrorDetail;

  constructor(public status: number, detail: ApiErrorDetail) {
    super(formatDetail(detail, status));
    this.detailRaw = detail;
  }

  /** Accessor de compat com consumidores antigos que esperam string. */
  get detail(): string {
    return formatDetail(this.detailRaw, this.status);
  }
}

/** Extrai `code` de um ApiError F9+. Retorna undefined se detail é string ou array. */
export function getErrorCode(err: unknown): string | undefined {
  if (!(err instanceof ApiError)) return undefined;
  const d = err.detailRaw;
  if (typeof d !== "object" || d === null || Array.isArray(d)) return undefined;
  return d.code;
}

// ─── Fetch Helpers ───

/** Hook global disparado quando backend retorna `token_revoked`.
 * Instalado por `AuthBootstrap` no root layout — quando dispara, força
 * logout + redirect para login. Exportado para testes. */
let onTokenRevoked: (() => void) | null = null;
export function setTokenRevokedHandler(handler: (() => void) | null) {
  onTokenRevoked = handler;
}

// ADR-170 · W3-T03 — refresh transparente: 401 genérico tenta POST
// /auth/refresh uma vez (cookie httpOnly viaja sozinho; o header custom é a
// defesa CSRF) e repete a request original. Promise compartilhada evita
// stampede intra-tab; a race inter-tab é coberta pela grace window do backend.
let refreshInFlight: Promise<string | null> | null = null;

// Endpoints onde refresh não faz sentido (evita recursão / loop em login).
const NO_REFRESH_PATHS = [
  "/auth/refresh",
  "/auth/login",
  "/auth/register",
  "/auth/logout",
];

async function requestRefreshedToken(): Promise<string | null> {
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "X-Refresh-Request": "1" },
    });
    if (!res.ok) return null;
    const body = (await res.json()) as { access_token?: string };
    return body.access_token ?? null;
  } catch {
    return null;
  }
}

function refreshAccessToken(): Promise<string | null> {
  if (!refreshInFlight) {
    refreshInFlight = requestRefreshedToken().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

function buildHeaders(options: RequestInit): Record<string, string> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (!headers["Content-Type"] && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  return headers;
}

function isTokenRevoked(detail: ApiErrorDetail): boolean {
  return (
    typeof detail === "object" &&
    !Array.isArray(detail) &&
    detail?.code === "token_revoked"
  );
}

async function parseSuccess<T>(res: Response): Promise<T> {
  if (res.status === 204) return undefined as T;
  return res.json();
}

async function parseDetail(res: Response): Promise<ApiErrorDetail> {
  const body = (await res.json().catch(() => ({}))) as {
    detail?: ApiErrorDetail;
  };
  return body.detail ?? `HTTP ${res.status}`;
}

async function retryAfterRefresh<T>(
  path: string,
  options: RequestInit
): Promise<T> {
  const retry = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: buildHeaders(options),
  });
  if (retry.ok) return parseSuccess<T>(retry);
  throw new ApiError(retry.status, await parseDetail(retry));
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: buildHeaders(options),
  });
  if (res.ok) return parseSuccess<T>(res);

  const detail = await parseDetail(res);

  // F9.2 · forced logout — token_revoked nunca tenta refresh (tv bumped →
  // a família de refresh também já era; backend revoga na rotação).
  if (res.status === 401 && isTokenRevoked(detail)) {
    clearToken();
    if (onTokenRevoked) onTokenRevoked();
    throw new ApiError(res.status, detail);
  }

  const refreshable =
    res.status === 401 && !!getToken() && !NO_REFRESH_PATHS.includes(path);
  if (refreshable) {
    const refreshed = await refreshAccessToken();
    if (refreshed !== null) {
      setToken(refreshed);
      return retryAfterRefresh<T>(path, options);
    }
    clearToken();
  }

  throw new ApiError(res.status, detail);
}
