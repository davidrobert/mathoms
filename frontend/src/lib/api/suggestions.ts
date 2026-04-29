// Direção E · Onda 5 · ADR-153 — Suggestion aggregate (proposal imutável).
// Money no wire é string decimal (ADR-090). Frontend converte string → number
// só na renderização do <MonetaryValue/>.

import { apiFetch } from "./core";

/** Direção E · Onda 5 · ADR-153 — status do aggregate Suggestion.
 * Não confundir com `SuggestionStatus` de `tasks.ts` (TaskSuggestion E5.N
 * com lower-case `pending|approved|rejected|merged`). */
export type SuggestionAggregateStatus =
  | "Pendente"
  | "Aceita"
  | "Modificada"
  | "Descartada";

export type SuggestionSeverity = "info" | "warning" | "danger";

export type SuggestionAggregateOrigin = "deterministic" | "llm";

export type SuggestionKind =
  | "trs_desalinhada"
  | "reserva_insuficiente"
  | "alocacao_fora_alvo"
  | "aporte_abaixo_meta"
  | "dolarizacao_atrasada";

export type DismissReason =
  | "ja_considerei"
  | "nao_se_aplica"
  | "discordo_diagnostico"
  | "adiar"
  | "outro";

export const DISMISS_REASON_LABELS: Record<DismissReason, string> = {
  ja_considerei: "Já considerei",
  nao_se_aplica: "Não se aplica",
  discordo_diagnostico: "Discordo do diagnóstico",
  adiar: "Adiar",
  outro: "Outro",
};

export interface Suggestion {
  id: string;
  workspace_id: string;
  report_id: string | null;
  section_id: string;
  kind: SuggestionKind | string;
  origin: SuggestionAggregateOrigin | string;
  severity: SuggestionSeverity;
  title: string;
  rationale: string;
  /** Decimal string (ex.: "9000.00"). Null quando não envolve valor monetário. */
  amount_brl: string | null;
  status: SuggestionAggregateStatus;
  accepted_decision_id: string | null;
  dismissed_reason: DismissReason | string | null;
  accepted_at: string | null;
  dismissed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SuggestionListResponse {
  suggestions: Suggestion[];
  total: number;
}

export interface SuggestionCountResponse {
  count: number;
  status: string | null;
}

export interface SuggestionRegenerateResponse {
  created: number;
  skipped_dedup: number;
  skipped_cap: number;
  total_drafts: number;
  suggestions: Suggestion[];
}

export interface AcceptSuggestionPayload {
  decision_code: string;
  note?: string | null;
}

export interface ModifySuggestionPayload {
  decision_code: string;
  title?: string | null;
  rationale?: string | null;
  amount_brl?: string | null;
  note?: string | null;
}

export interface DismissSuggestionPayload {
  reason: DismissReason;
  note?: string | null;
}

export async function listSuggestions(
  workspaceId: string,
  status?: SuggestionAggregateStatus,
): Promise<SuggestionListResponse> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiFetch<SuggestionListResponse>(
    `/workspaces/${workspaceId}/suggestions${qs}`,
  );
}

export async function countSuggestions(
  workspaceId: string,
  status: SuggestionAggregateStatus = "Pendente",
): Promise<SuggestionCountResponse> {
  return apiFetch<SuggestionCountResponse>(
    `/workspaces/${workspaceId}/suggestions/count?status=${encodeURIComponent(status)}`,
  );
}

export async function getSuggestion(
  workspaceId: string,
  suggestionId: string,
): Promise<Suggestion> {
  return apiFetch<Suggestion>(
    `/workspaces/${workspaceId}/suggestions/${suggestionId}`,
  );
}

export async function acceptSuggestion(
  workspaceId: string,
  suggestionId: string,
  payload: AcceptSuggestionPayload,
): Promise<Suggestion> {
  return apiFetch<Suggestion>(
    `/workspaces/${workspaceId}/suggestions/${suggestionId}/accept`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export async function modifySuggestion(
  workspaceId: string,
  suggestionId: string,
  payload: ModifySuggestionPayload,
): Promise<Suggestion> {
  return apiFetch<Suggestion>(
    `/workspaces/${workspaceId}/suggestions/${suggestionId}/modify`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export async function dismissSuggestion(
  workspaceId: string,
  suggestionId: string,
  payload: DismissSuggestionPayload,
): Promise<Suggestion> {
  return apiFetch<Suggestion>(
    `/workspaces/${workspaceId}/suggestions/${suggestionId}/dismiss`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export async function regenerateSuggestionsForReport(
  workspaceId: string,
  reportId: string,
): Promise<SuggestionRegenerateResponse> {
  return apiFetch<SuggestionRegenerateResponse>(
    `/workspaces/${workspaceId}/reports/${reportId}/regenerate-suggestions`,
    { method: "POST", body: JSON.stringify({}) },
  );
}
