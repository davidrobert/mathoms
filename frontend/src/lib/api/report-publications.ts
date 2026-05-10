/** Report publications API client (ADR-186). */

import { apiFetch } from "./core";

export interface ReportPublicationResponse {
  id: string;
  workspace_id: string;
  period_yyyymm: string;
  artifact_id: number;
  published_at: string;
  published_by: string;
  immutable_hash: string;
  unpublished_at: string | null;
}

export interface ReportPublicationListResponse {
  items: ReportPublicationResponse[];
}

/** Normaliza `period` (`2026-04` ou `202604`) para o formato `YYYYMM` exigido pela API. */
export function normalizePeriodYyyymm(period: string | null | undefined): string | null {
  if (!period) return null;
  const digits = period.replace(/\D/g, "");
  return digits.length === 6 ? digits : null;
}

export async function getActivePublication(
  workspaceId: string,
  periodYyyymm: string,
): Promise<ReportPublicationResponse | null> {
  return apiFetch(
    `/workspaces/${workspaceId}/reports/${periodYyyymm}/publication`,
  );
}

export async function listPublications(
  workspaceId: string,
): Promise<ReportPublicationListResponse> {
  return apiFetch(`/workspaces/${workspaceId}/reports/publications`);
}

export async function publishMonth(
  workspaceId: string,
  periodYyyymm: string,
  artifactId: number,
): Promise<ReportPublicationResponse> {
  return apiFetch(`/workspaces/${workspaceId}/reports/${periodYyyymm}/publish`, {
    method: "POST",
    body: JSON.stringify({ artifact_id: artifactId }),
    headers: { "Content-Type": "application/json" },
  });
}

export async function unpublishMonth(
  workspaceId: string,
  periodYyyymm: string,
): Promise<void> {
  await apiFetch(
    `/workspaces/${workspaceId}/reports/${periodYyyymm}/publish`,
    { method: "DELETE" },
  );
}
