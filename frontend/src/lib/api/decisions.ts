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

/** ADR-162 — caminho dot-notation indicando qual campo de Goal a
 * Decision atualiza ao virar Executada. */
export type DecisionTargetField =
  | "goal.if.trs_pct"
  | "goal.if.renda_passiva_mensal_brl"
  | "goal.if.horizonte_anos"
  | "goal.aporte.meta_aporte_mensal_brl"
  | "goal.dolar.meta_usd"
  | "goal.dolar.aporte_mensal_brl";

export type DecisionTargetValueType = "pct" | "brl" | "int" | "str";

/** ADR-179 — horizonte temporal da Decision. Default ``short_6_12m``. */
export type DecisionHorizon = "short_6_12m" | "medium_1_3y" | "long_5y_plus";

export const DECISION_HORIZON_LABEL: Record<DecisionHorizon, string> = {
  short_6_12m: "Curto (6–12 meses)",
  medium_1_3y: "Médio (1–3 anos)",
  long_5y_plus: "Longo (5+ anos)",
};

export const DECISION_HORIZON_ORDER: ReadonlyArray<DecisionHorizon> = [
  "short_6_12m",
  "medium_1_3y",
  "long_5y_plus",
];

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
  /** ADR-162 — projection target. */
  target_field: DecisionTargetField | string | null;
  target_value: string | null;
  target_value_type: DecisionTargetValueType | string | null;
  /** ADR-163 — KPIs frozen do relatório-fonte da Suggestion. */
  context_snapshot: Record<string, unknown> | null;
  /** ADR-179 — quantificação de impacto + horizonte + prioridade. */
  impact_1y_brl: string | null;
  impact_10y_brl: string | null;
  horizon: DecisionHorizon;
  /** 1..99; null ordena por impact_1y DESC NULLS LAST no card S10. */
  priority: number | null;
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
  /** ADR-162 — projection target. */
  target_field?: DecisionTargetField | string | null;
  target_value?: string | null;
  target_value_type?: DecisionTargetValueType | null;
  /** ADR-163 — KPIs frozen do relatório-fonte (preenchido auto pelo
   * backend ao aceitar Suggestion; UI raramente passa). */
  context_snapshot?: Record<string, unknown> | null;
  /** ADR-179 — quantificação de impacto + horizonte + prioridade. */
  impact_1y_brl?: string | null;
  impact_10y_brl?: string | null;
  horizon?: DecisionHorizon;
  priority?: number | null;
}

export interface DecisionUpdatePayload {
  title?: string;
  rationale?: string | null;
  amount_brl?: string | null;
  status?: DecisionStatus;
  decided_at?: string | null;
  /** ADR-179. */
  impact_1y_brl?: string | null;
  impact_10y_brl?: string | null;
  horizon?: DecisionHorizon;
  priority?: number | null;
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
