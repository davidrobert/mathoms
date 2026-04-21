import { apiFetch } from "./core";

// ─── Vault Types ───

export interface VaultPasswordResponse {
  id: string;
  label: string;
  created_at: string;
}

export interface VaultListResponse {
  passwords: VaultPasswordResponse[];
  total: number;
}

// ─── Vault ───

export async function listVaultPasswords(workspaceId: string): Promise<VaultListResponse> {
  return apiFetch(`/workspaces/${workspaceId}/vault/passwords`);
}

export async function createVaultPassword(
  workspaceId: string,
  label: string,
  password: string
): Promise<VaultPasswordResponse> {
  return apiFetch(`/workspaces/${workspaceId}/vault/passwords`, {
    method: "POST",
    body: JSON.stringify({ label, password }),
  });
}

export async function deleteVaultPassword(workspaceId: string, passwordId: string): Promise<void> {
  return apiFetch(`/workspaces/${workspaceId}/vault/passwords/${passwordId}`, { method: "DELETE" });
}
