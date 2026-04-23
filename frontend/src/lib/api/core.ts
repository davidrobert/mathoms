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
      !Array.isArray(detail) &&
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
