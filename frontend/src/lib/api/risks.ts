// A10.4 · ADR-178 — Risk aggregate (workspace-scoped).
// Decision = ação a tomar; Risk = evento incerto. Link via
// `mitigations_decision_ids`. Money no wire em string decimal (ADR-090).

import { apiFetch } from "./core";

export type RiskProbability = "baixa" | "média" | "alta";

export type RiskImpactLevel = "baixo" | "médio" | "alto" | "crítico";

export type RiskStatus = "Ativo" | "Mitigado" | "Aceito" | "Descartado";

export interface Risk {
  id: string;
  workspace_id: string;
  code: string;
  name: string;
  rationale: string;
  probability: RiskProbability | null;
  impact_level: RiskImpactLevel;
  /** Decimal string (ex.: "300000.00"). Null quando não quantificado. */
  impact_brl: string | null;
  status: RiskStatus;
  mitigations_decision_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface RiskListResponse {
  risks: Risk[];
  total: number;
}

export interface RiskCreatePayload {
  code: string;
  name: string;
  rationale: string;
  probability?: RiskProbability | null;
  impact_level: RiskImpactLevel;
  impact_brl?: string | null;
  status?: RiskStatus;
  mitigations_decision_ids?: string[];
}

export interface RiskUpdatePayload {
  name?: string;
  rationale?: string;
  probability?: RiskProbability | null;
  impact_level?: RiskImpactLevel;
  impact_brl?: string | null;
  status?: RiskStatus;
}

export interface RiskMitigationLinkPayload {
  decision_id: string;
}

export async function listRisks(
  workspaceId: string,
): Promise<RiskListResponse> {
  return apiFetch<RiskListResponse>(`/workspaces/${workspaceId}/risks`);
}

export async function getRisk(
  workspaceId: string,
  riskId: string,
): Promise<Risk> {
  return apiFetch<Risk>(`/workspaces/${workspaceId}/risks/${riskId}`);
}

export async function createRisk(
  workspaceId: string,
  payload: RiskCreatePayload,
): Promise<Risk> {
  return apiFetch<Risk>(`/workspaces/${workspaceId}/risks`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateRisk(
  workspaceId: string,
  riskId: string,
  payload: RiskUpdatePayload,
): Promise<Risk> {
  return apiFetch<Risk>(`/workspaces/${workspaceId}/risks/${riskId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteRisk(
  workspaceId: string,
  riskId: string,
): Promise<void> {
  await apiFetch<void>(`/workspaces/${workspaceId}/risks/${riskId}`, {
    method: "DELETE",
  });
}

export async function linkMitigation(
  workspaceId: string,
  riskId: string,
  payload: RiskMitigationLinkPayload,
): Promise<Risk> {
  return apiFetch<Risk>(
    `/workspaces/${workspaceId}/risks/${riskId}/mitigations`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export async function unlinkMitigation(
  workspaceId: string,
  riskId: string,
  decisionId: string,
): Promise<Risk> {
  return apiFetch<Risk>(
    `/workspaces/${workspaceId}/risks/${riskId}/mitigations/${decisionId}`,
    { method: "DELETE" },
  );
}
