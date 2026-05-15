import { apiFetch } from "./core";

// ─── Properties (ADR-215 P4) ───

export type Classification =
  | "residencia_principal"
  | "uso_pessoal"
  | "locado"
  | "comercial"
  | "especulacao"
  | "desconhecido";

export type OverrideSource =
  | "user_manual"
  | "fuzzy_match_accepted"
  | "migration_keyword";

export type ResidenciaStatus = "owned" | "rented" | "undeclared";

export interface PropertyResponse {
  property_id: string;
  titular_key: string;
  codigo_rfb: string;
  descricao_sample: string | null;
  endereco_canonical: string | null;
  first_seen_year: number;
  low_confidence: boolean;
  classification: Classification | null;
  override_source: OverrideSource | null;
  classification_set_at: string | null;
  suggested_score: number | null;
  suggested_residencia_principal: boolean;
}

export interface PropertyListResponse {
  workspace_id: string;
  residencia_status: ResidenciaStatus;
  properties: PropertyResponse[];
}

export async function listProperties(workspaceId: string): Promise<PropertyListResponse> {
  return apiFetch(`/workspaces/${workspaceId}/properties`);
}

export async function setPropertyClassification(
  workspaceId: string,
  propertyId: string,
  classification: Classification,
  overrideSource: OverrideSource = "user_manual",
): Promise<PropertyResponse> {
  return apiFetch(`/workspaces/${workspaceId}/properties/${propertyId}/classification`, {
    method: "PUT",
    body: JSON.stringify({ classification, override_source: overrideSource }),
  });
}

export async function setResidenciaStatus(
  workspaceId: string,
  status: ResidenciaStatus,
): Promise<{ workspace_id: string; status: ResidenciaStatus }> {
  return apiFetch(`/workspaces/${workspaceId}/residencia-status`, {
    method: "PUT",
    body: JSON.stringify({ status }),
  });
}
