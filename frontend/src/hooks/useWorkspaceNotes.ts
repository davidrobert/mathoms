"use client";

// ADR-153 — hook do aggregate WorkspaceNotes (notas livres por workspace).
// Carrega lista pinned-first do workspace e expõe CRUD; cada mutação refaz
// o fetch para refletir reordenação por updated_at desc.

import { useCallback, useEffect, useState } from "react";

import {
  ApiError,
  createWorkspaceNote,
  deleteWorkspaceNote,
  listWorkspaceNotes,
  updateWorkspaceNote,
  type WorkspaceNote,
  type WorkspaceNoteCreatePayload,
  type WorkspaceNoteUpdatePayload,
} from "@/lib/api";

export interface UseWorkspaceNotesState {
  notes: WorkspaceNote[];
  loading: boolean;
  error: string;
  reload: () => Promise<void>;
  create: (payload?: WorkspaceNoteCreatePayload) => Promise<WorkspaceNote>;
  update: (noteId: string, payload: WorkspaceNoteUpdatePayload) => Promise<WorkspaceNote>;
  remove: (noteId: string) => Promise<void>;
}

type Reload = () => Promise<void>;

function describeError(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.detail : fallback;
}

interface ReloadDeps {
  workspaceId: string | undefined;
  setNotes: (n: WorkspaceNote[]) => void;
  setLoading: (b: boolean) => void;
  setError: (s: string) => void;
}

function useNotesReload({ workspaceId, setNotes, setLoading, setError }: ReloadDeps): Reload {
  return useCallback(async () => {
    if (!workspaceId) {
      setNotes([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const resp = await listWorkspaceNotes(workspaceId);
      setNotes(resp.notes);
    } catch (err) {
      setError(describeError(err, "Erro ao carregar notas"));
    } finally {
      setLoading(false);
    }
  }, [workspaceId, setNotes, setLoading, setError]);
}

function useCreate(workspaceId: string | undefined, reload: Reload) {
  return useCallback(
    async (payload: WorkspaceNoteCreatePayload = {}): Promise<WorkspaceNote> => {
      if (!workspaceId) throw new Error("Workspace não selecionado");
      const created = await createWorkspaceNote(workspaceId, payload);
      await reload();
      return created;
    },
    [workspaceId, reload],
  );
}

function useUpdate(workspaceId: string | undefined, reload: Reload) {
  return useCallback(
    async (noteId: string, payload: WorkspaceNoteUpdatePayload): Promise<WorkspaceNote> => {
      if (!workspaceId) throw new Error("Workspace não selecionado");
      const updated = await updateWorkspaceNote(workspaceId, noteId, payload);
      await reload();
      return updated;
    },
    [workspaceId, reload],
  );
}

function useRemove(workspaceId: string | undefined, reload: Reload) {
  return useCallback(
    async (noteId: string) => {
      if (!workspaceId) return;
      await deleteWorkspaceNote(workspaceId, noteId);
      await reload();
    },
    [workspaceId, reload],
  );
}

export function useWorkspaceNotes(workspaceId: string | undefined): UseWorkspaceNotesState {
  const [notes, setNotes] = useState<WorkspaceNote[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const reload = useNotesReload({ workspaceId, setNotes, setLoading, setError });
  const create = useCreate(workspaceId, reload);
  const update = useUpdate(workspaceId, reload);
  const remove = useRemove(workspaceId, reload);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { notes, loading, error, reload, create, update, remove };
}
