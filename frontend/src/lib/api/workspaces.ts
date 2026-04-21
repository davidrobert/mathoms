import { API_BASE, ApiError, apiFetch } from "./core";

// ═══════════════════════════════════════════════════════════════════════
// Workspaces (F8) — listagem de memberships do usuário
// ═══════════════════════════════════════════════════════════════════════

/** Papel do usuário em um workspace.
 * UI labels (pt-BR) definidos em `frontend/src/lib/roleLabels.ts`:
 *   owner  → "Responsável"
 *   member → "Coadministrador"
 *   viewer → "Acompanha"
 */
export type WorkspaceRole = "owner" | "member" | "viewer";

/** Papéis que podem ser atribuídos via convite (owner nunca é convidável). */
export type InvitableRole = "member" | "viewer";

export interface UserWorkspace {
  id: string;
  name: string;
  family_surname: string | null;
  role: WorkspaceRole;
  joined_at: string;
}

export interface UserWorkspaceList {
  workspaces: UserWorkspace[];
  total: number;
}

export async function listMyWorkspaces(): Promise<UserWorkspaceList> {
  return apiFetch("/me/workspaces");
}

// ═══════════════════════════════════════════════════════════════════════
// Members & Invitations (F9 — workspace sharing)
// ═══════════════════════════════════════════════════════════════════════

export interface WorkspaceMemberResponse {
  user_id: string;
  email: string;
  full_name: string;
  role: WorkspaceRole;
  joined_at: string;
  invited_by: string | null;
}

export interface WorkspaceMemberList {
  members: WorkspaceMemberResponse[];
  total: number;
}

export type InvitationStatus = "pending" | "accepted" | "revoked" | "expired";

export interface InvitationResponse {
  id: string;
  workspace_id: string;
  email: string;
  role: WorkspaceRole;
  status: InvitationStatus;
  invited_by: string | null;
  expires_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
  created_at: string;
}

export interface InvitationCreateResponse {
  invitation: InvitationResponse;
  /** Token cru — exposto apenas uma vez. Copie o `invite_path` ou monte a
   * URL absoluta com `window.location.origin + invite_path` pra
   * enviar ao convidado. */
  token: string;
  invite_path: string;
}

export interface InvitationListResponse {
  invitations: InvitationResponse[];
  total: number;
}

export interface InvitationPreviewResponse {
  workspace_name: string;
  workspace_family_surname: string | null;
  role: WorkspaceRole;
  invited_by_name: string | null;
  invited_by_email: string | null;
  email: string;
  expires_at: string;
  status: InvitationStatus;
}

export interface InvitationAcceptResponse {
  workspace_id: string;
  role: WorkspaceRole;
  joined_at: string;
}

export async function listWorkspaceMembers(
  workspaceId: string
): Promise<WorkspaceMemberList> {
  return apiFetch(`/workspaces/${workspaceId}/members`);
}

export async function updateMemberRole(
  workspaceId: string,
  userId: string,
  role: InvitableRole
): Promise<WorkspaceMemberResponse> {
  return apiFetch(`/workspaces/${workspaceId}/members/${userId}`, {
    method: "PATCH",
    body: JSON.stringify({ role }),
  });
}

export async function removeWorkspaceMember(
  workspaceId: string,
  userId: string
): Promise<void> {
  return apiFetch(`/workspaces/${workspaceId}/members/${userId}`, {
    method: "DELETE",
  });
}

export async function listWorkspaceInvitations(
  workspaceId: string,
  opts: { onlyPending?: boolean } = {}
): Promise<InvitationListResponse> {
  const qs = opts.onlyPending ? "?only_pending=true" : "";
  return apiFetch(`/workspaces/${workspaceId}/invitations${qs}`);
}

export async function createWorkspaceInvitation(
  workspaceId: string,
  email: string,
  role: InvitableRole
): Promise<InvitationCreateResponse> {
  return apiFetch(`/workspaces/${workspaceId}/invitations`, {
    method: "POST",
    body: JSON.stringify({ email, role }),
  });
}

export async function revokeWorkspaceInvitation(
  workspaceId: string,
  invitationId: string
): Promise<void> {
  return apiFetch(`/workspaces/${workspaceId}/invitations/${invitationId}`, {
    method: "DELETE",
  });
}

/** Rota pública — não envia token de auth. */
export async function previewInvitation(
  token: string
): Promise<InvitationPreviewResponse> {
  const res = await fetch(`${API_BASE}/invitations/${token}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/** Precisa de auth (user logado). */
export async function acceptInvitation(
  token: string
): Promise<InvitationAcceptResponse> {
  return apiFetch(`/invitations/${token}/accept`, { method: "POST" });
}
