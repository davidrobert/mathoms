// A7.2a · ADR-136 — Decision aggregate (event-sourced).
// Entidade editorial do plano de ação. Money no wire é string decimal
// (ADR-090). Frontend converte string → number só na renderização do
// <MonetaryValue/> (cents → BRL preservados).

import { apiFetch } from "./core";

export type DecisionStatus =
  | "Pendente"
  | "Decidido"
  | "Executado"
  | "Descartado"
  | "Superseded";

export interface Decision {
  id: string;
  workspace_id: string;
  code: string;
  title: string;
  rationale: string | null;
  /** Decimal string (ex.: "117430.00"). Null quando a Decision não tem valor monetário. */
  amount_brl: string | null;
  status: DecisionStatus;
  supersedes_id: string | null;
  decided_at: string | null;
  executed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DecisionListResponse {
  decisions: Decision[];
  total: number;
}

export interface DecisionCreatePayload {
  code: string;
  title: string;
  rationale?: string | null;
  amount_brl?: string | null;
  status?: DecisionStatus;
  decided_at?: string | null;
}

export interface DecisionUpdatePayload {
  title?: string;
  rationale?: string | null;
  amount_brl?: string | null;
  status?: DecisionStatus;
  decided_at?: string | null;
}

export interface DecisionExecutePayload {
  executed_at?: string | null;
  note?: string | null;
}

export interface DecisionSupersedePayload {
  superseded_by_id: string;
  note?: string | null;
}

export async function listDecisions(workspaceId: string): Promise<DecisionListResponse> {
  return apiFetch<DecisionListResponse>(`/workspaces/${workspaceId}/decisions`);
}

export async function getDecision(workspaceId: string, decisionId: string): Promise<Decision> {
  return apiFetch<Decision>(`/workspaces/${workspaceId}/decisions/${decisionId}`);
}

export async function createDecision(
  workspaceId: string,
  payload: DecisionCreatePayload,
): Promise<Decision> {
  return apiFetch<Decision>(`/workspaces/${workspaceId}/decisions`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateDecision(
  workspaceId: string,
  decisionId: string,
  payload: DecisionUpdatePayload,
): Promise<Decision> {
  return apiFetch<Decision>(`/workspaces/${workspaceId}/decisions/${decisionId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function executeDecision(
  workspaceId: string,
  decisionId: string,
  payload: DecisionExecutePayload = {},
): Promise<Decision> {
  return apiFetch<Decision>(`/workspaces/${workspaceId}/decisions/${decisionId}/execute`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function supersedeDecision(
  workspaceId: string,
  oldDecisionId: string,
  payload: DecisionSupersedePayload,
): Promise<Decision> {
  return apiFetch<Decision>(`/workspaces/${workspaceId}/decisions/${oldDecisionId}/supersede`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
