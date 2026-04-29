// ADR-153 — WorkspaceNotes (notas livres por workspace, multi-row, com pin).

import { apiFetch } from "./core";

export interface WorkspaceNote {
  id: string;
  workspace_id: string;
  title: string | null;
  content: string;
  pinned: boolean;
  author_user_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceNoteListResponse {
  notes: WorkspaceNote[];
  total: number;
}

export interface WorkspaceNoteCreatePayload {
  title?: string | null;
  content?: string;
  pinned?: boolean;
}

export interface WorkspaceNoteUpdatePayload {
  title?: string | null;
  content?: string;
  pinned?: boolean;
}

export async function listWorkspaceNotes(
  workspaceId: string,
): Promise<WorkspaceNoteListResponse> {
  return apiFetch<WorkspaceNoteListResponse>(`/workspaces/${workspaceId}/notes`);
}

export async function createWorkspaceNote(
  workspaceId: string,
  payload: WorkspaceNoteCreatePayload,
): Promise<WorkspaceNote> {
  return apiFetch<WorkspaceNote>(`/workspaces/${workspaceId}/notes`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateWorkspaceNote(
  workspaceId: string,
  noteId: string,
  payload: WorkspaceNoteUpdatePayload,
): Promise<WorkspaceNote> {
  return apiFetch<WorkspaceNote>(`/workspaces/${workspaceId}/notes/${noteId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteWorkspaceNote(
  workspaceId: string,
  noteId: string,
): Promise<void> {
  await apiFetch<void>(`/workspaces/${workspaceId}/notes/${noteId}`, {
    method: "DELETE",
  });
}
