// A11.W5 · ADR-192 · S9-T05 — Protection aggregate (workspace-scoped).
// Apólices contratadas. Money no wire em string decimal (ADR-090).
// `policy_ref` nunca cruza o wire em plaintext — backend retorna apenas
// `policy_ref_masked` (últimos 4 chars). UI mostra mascarado por default.

import { apiFetch } from "./core";

export type ProtectionCategory =
  | "vida"
  | "invalidez"
  | "saude"
  | "patrimonial"
  | "rc_profissional"
  | "sucessorio";

export type ProtectionStatus = "Ativa" | "Suspensa" | "Cancelada" | "Vencida";

export type ProtectionCoverageType = "term" | "whole" | "universal";

export const PROTECTION_CATEGORIES: ReadonlyArray<{
  value: ProtectionCategory;
  label: string;
}> = [
  { value: "vida", label: "Vida" },
  { value: "invalidez", label: "Invalidez" },
  { value: "saude", label: "Saúde" },
  { value: "patrimonial", label: "Patrimonial" },
  { value: "rc_profissional", label: "RC Profissional" },
  { value: "sucessorio", label: "Sucessório" },
];

export const PROTECTION_STATUSES: ReadonlyArray<{
  value: ProtectionStatus;
  label: string;
}> = [
  { value: "Ativa", label: "Ativa" },
  { value: "Suspensa", label: "Suspensa" },
  { value: "Vencida", label: "Vencida" },
  { value: "Cancelada", label: "Cancelada" },
];

export const PROTECTION_COVERAGE_TYPES: ReadonlyArray<{
  value: ProtectionCoverageType;
  label: string;
}> = [
  { value: "term", label: "Term (temporário)" },
  { value: "whole", label: "Whole (vitalício)" },
  { value: "universal", label: "Universal" },
];

export interface Protection {
  id: string;
  workspace_id: string;
  category: ProtectionCategory;
  holder_family_member_id: string | null;
  insurer: string | null;
  /** Mascarado por default — apenas últimos 4 chars (ex.: "***1234"). */
  policy_ref_masked: string | null;
  /** Decimal string (ex.: "300000.00"). */
  coverage_brl: string;
  premium_monthly_brl: string | null;
  coverage_type: ProtectionCoverageType | null;
  starts_at: string;
  ends_at: string | null;
  status: ProtectionStatus;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProtectionListResponse {
  protections: Protection[];
  total: number;
}

export interface ProtectionCreatePayload {
  category: ProtectionCategory;
  holder_family_member_id?: string | null;
  insurer?: string | null;
  policy_ref?: string | null;
  coverage_brl: string;
  premium_monthly_brl?: string | null;
  coverage_type?: ProtectionCoverageType | null;
  starts_at: string;
  ends_at?: string | null;
  status?: ProtectionStatus;
  notes?: string | null;
}

export interface ProtectionUpdatePayload {
  holder_family_member_id?: string | null;
  insurer?: string | null;
  policy_ref?: string | null;
  coverage_brl?: string;
  premium_monthly_brl?: string | null;
  coverage_type?: ProtectionCoverageType | null;
  starts_at?: string;
  ends_at?: string | null;
  notes?: string | null;
}

export interface ProtectionCancelPayload {
  reason?: string | null;
}

// ─── Bundle (ADR-192 §D2) ───

export interface ProtectionBundleItem {
  id: string;
  category: ProtectionCategory;
  holder_family_member_id: string | null;
  insurer: string | null;
  coverage_brl: string;
  premium_monthly_brl: string | null;
  coverage_type: ProtectionCoverageType | null;
  starts_at: string;
  ends_at: string | null;
  status: ProtectionStatus;
}

export interface ProtectionGapItem {
  ideal_brl: string | null;
  actual_brl: string;
  gap_brl: string | null;
  methodology: string | null;
}

export interface ProtectionRecommendation {
  category: string;
  rationale: string;
  priority: string;
}

export interface RiskInferred {
  category: string;
  name: string;
  rationale: string;
  estimated_impact_brl: string | null;
  source_calculator: string;
}

export interface ProtectionThresholds {
  life_insurance_multiple_renda_anual: number | null;
  reserva_meses_clt: number | null;
  reserva_meses_pj: number | null;
  reserva_meses_socio_variavel: number | null;
  fbar_threshold_usd: number | null;
  estate_tax_threshold_usd: number | null;
}

export interface ProtectionBundle {
  policies: ProtectionBundleItem[];
  gap_analysis: Record<string, ProtectionGapItem>;
  recommendations: ProtectionRecommendation[];
  auto_inferred_risks: RiskInferred[];
  methodology_thresholds: ProtectionThresholds;
  has_us_exposure: boolean;
  adapter_version: number;
}

// ─── HTTP clients ───

export async function listProtections(
  workspaceId: string,
): Promise<ProtectionListResponse> {
  return apiFetch<ProtectionListResponse>(
    `/workspaces/${workspaceId}/protections`,
  );
}

export async function getProtection(
  workspaceId: string,
  protectionId: string,
): Promise<Protection> {
  return apiFetch<Protection>(
    `/workspaces/${workspaceId}/protections/${protectionId}`,
  );
}

export async function createProtection(
  workspaceId: string,
  payload: ProtectionCreatePayload,
): Promise<Protection> {
  return apiFetch<Protection>(`/workspaces/${workspaceId}/protections`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateProtection(
  workspaceId: string,
  protectionId: string,
  payload: ProtectionUpdatePayload,
): Promise<Protection> {
  return apiFetch<Protection>(
    `/workspaces/${workspaceId}/protections/${protectionId}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
  );
}

export async function cancelProtection(
  workspaceId: string,
  protectionId: string,
  payload: ProtectionCancelPayload = {},
): Promise<Protection> {
  return apiFetch<Protection>(
    `/workspaces/${workspaceId}/protections/${protectionId}/cancel`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export async function getProtectionBundle(
  workspaceId: string,
): Promise<ProtectionBundle> {
  return apiFetch<ProtectionBundle>(
    `/workspaces/${workspaceId}/protection-bundle`,
  );
}
