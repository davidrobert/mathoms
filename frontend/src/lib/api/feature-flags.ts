import { apiFetch } from "./core";

// ─── Feature Flags (F8.3) ────────────────────────────────────────────

export interface FeatureFlagsResponse {
  flags: Record<string, boolean>;
}

export async function getFeatureFlags(
  workspaceId: string
): Promise<FeatureFlagsResponse> {
  return apiFetch(`/workspaces/${workspaceId}/feature-flags`);
}

export async function setFeatureFlag(
  workspaceId: string,
  flag: string,
  enabled: boolean
): Promise<FeatureFlagsResponse> {
  return apiFetch(`/workspaces/${workspaceId}/feature-flags/${flag}`, {
    method: "PUT",
    body: JSON.stringify({ enabled }),
  });
}
