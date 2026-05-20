import { apiFetch } from "./core";

// ─── PropertyMarketValue versionada append-only (ADR-227 §D2 · Sprint A15 Onda 4) ───

export type PmvSource =
  | "user_declared"
  | "avaliacao_terceiros"
  | "cep_proxy_futuro";

export interface PropertyMarketValueResponse {
  id: string;
  property_id: string;
  workspace_id: string;
  /** BRL como string decimal (ADR-090). */
  valor_brl: string;
  valuation_date: string;
  source: PmvSource;
  /** 0-1; null em user_declared. */
  confidence: string | null;
  notes: string | null;
  /** Quando setado, esta entry foi superseded (não retornada por latest_by_property). */
  superseded_by_id: string | null;
  created_at: string;
  created_by_user_id: string | null;
}

export interface PropertyMarketValueCreate {
  property_id: string;
  valor_brl: string;
  valuation_date: string;
  source?: PmvSource;
  confidence?: string | null;
  notes?: string | null;
}

export interface SupersedeRequest {
  superseded_by_id: string;
}

export async function listPropertyMarketValues(
  workspaceId: string,
  options: { propertyId?: string } = {},
): Promise<PropertyMarketValueResponse[]> {
  const query = options.propertyId ? `?property_id=${options.propertyId}` : "";
  return apiFetch(`/workspaces/${workspaceId}/property-market-values${query}`);
}

export async function createPropertyMarketValue(
  workspaceId: string,
  body: PropertyMarketValueCreate,
): Promise<PropertyMarketValueResponse> {
  return apiFetch(`/workspaces/${workspaceId}/property-market-values`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function supersedePropertyMarketValue(
  workspaceId: string,
  valueId: string,
  supersededById: string,
): Promise<PropertyMarketValueResponse> {
  return apiFetch(
    `/workspaces/${workspaceId}/property-market-values/${valueId}/supersede`,
    {
      method: "PATCH",
      body: JSON.stringify({ superseded_by_id: supersededById } satisfies SupersedeRequest),
    },
  );
}
