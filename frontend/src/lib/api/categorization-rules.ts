/**
 * Categorization Rules — learning loop (ADR-186/188 · A12 P3/P4).
 *
 * Endpoints expostos:
 *   POST   /workspaces/{ws}/categorization/rules/preview
 *   POST   /workspaces/{ws}/categorization/rules
 *   GET    /workspaces/{ws}/categorization/rules
 *   GET    /workspaces/{ws}/categorization/rules/{rule_id}/apply-status
 *   POST   /workspaces/{ws}/categorization/rules/{rule_id}/disable
 *   DELETE /workspaces/{ws}/categorization/rules/{rule_id}
 *
 * Gating: 403 ``learning_loop_disabled`` quando flag off.
 */
import { apiFetch } from "./core";

// ─── Request/Response types ───

export interface RulePreviewRequest {
  keyword: string;
  target_category: string;
  /** ``["202601", "202604"]`` — janela opcional (default: toda a base). */
  period_window?: [string, string] | null;
}

export interface WarningEntry {
  code: string;
  message: string;
}

export interface ConflictEntry {
  rule_id: string;
  target_category: string;
  priority: number;
}

export interface RulePreviewResponse {
  matches_total: number;
  matches_in_closed_months: number;
  matches_with_manual_override: number;
  matches_blocked_internal_transfers: number;
  matches_amount_total_brl_cents: number;
  matches_by_month: Record<string, number>;
  conflicts: ConflictEntry[];
  low_risk: boolean;
  requires_user_confirmation: boolean;
  warnings: WarningEntry[];
}

export interface CategorizationRuleCreate {
  keyword: string;
  target_category: string;
  priority?: number;
  origin_override_id?: string;
  confirmed_visualized_months_impact?: boolean;
}

export interface CategorizationRuleResponse {
  id: string;
  workspace_id: string;
  keyword: string;
  target_category: string;
  priority: number;
  enabled: boolean;
  origin_override_id: string | null;
  created_by_user_id: string | null;
  applied_count: number;
  revert_count_manual_edit: number;
  revert_count_rule_disabled: number;
  created_at: string;
  updated_at: string;
}

export interface AsyncRuleCreatedResponse {
  rule_id: string;
  workspace_id: string;
  status: "pending";
  job_id: string;
  message: string;
}

export interface RuleApplyStatusResponse {
  rule_id: string;
  workspace_id: string;
  status: "pending" | "completed" | "failed" | "unknown";
  job_id?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  applied_count: number;
  failed_count: number;
  error?: string | null;
}

/** Discriminated union: 201 sync vs 202 async. */
export type CreateRuleResult =
  | { kind: "sync"; rule: CategorizationRuleResponse }
  | { kind: "async"; pending: AsyncRuleCreatedResponse };

// ─── API calls ───

export async function previewCategorizationRule(
  workspaceId: string,
  body: RulePreviewRequest,
): Promise<RulePreviewResponse> {
  return apiFetch(`/workspaces/${workspaceId}/categorization/rules/preview`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

async function _throwApiError(res: Response): Promise<never> {
  const detail = await res.json().catch(() => ({}));
  const { ApiError } = await import("./core");
  throw new ApiError(res.status, detail.detail ?? `HTTP ${res.status}`);
}

/** POST que distingue 201 (sync) de 202 (async background apply).
 *  ``apiFetch`` retorna o JSON sem o status code — leitura via fetch nativo. */
export async function createCategorizationRule(
  workspaceId: string,
  body: CategorizationRuleCreate,
): Promise<CreateRuleResult> {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("fin_token") : null;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(
    `/api/v1/workspaces/${workspaceId}/categorization/rules`,
    { method: "POST", headers, body: JSON.stringify(body) },
  );
  if (!res.ok) await _throwApiError(res);
  const payload = await res.json();
  return res.status === 202
    ? { kind: "async", pending: payload as AsyncRuleCreatedResponse }
    : { kind: "sync", rule: payload as CategorizationRuleResponse };
}

export async function getRuleApplyStatus(
  workspaceId: string,
  ruleId: string,
): Promise<RuleApplyStatusResponse> {
  return apiFetch(
    `/workspaces/${workspaceId}/categorization/rules/${ruleId}/apply-status`,
  );
}
