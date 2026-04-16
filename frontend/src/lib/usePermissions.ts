"use client";

/**
 * Hooks de permissão derivados do role do user no workspace atual (F9).
 *
 * Esta é a camada de UI — o backend já bloqueia escritas de `viewer` com
 * `require_write_role`, então estes hooks servem para UX (esconder botões,
 * desabilitar forms), não para segurança.
 */

import { useCurrentWorkspace } from "./useCurrentWorkspace";

interface Permissions {
  isOwner: boolean;
  isMember: boolean;
  isViewer: boolean;
  /** Pode editar (metas, transações, documentos): owner + member */
  canWrite: boolean;
  /** Pode gerenciar membros: só owner */
  canManageMembers: boolean;
  /** Está aguardando o workspace carregar */
  isLoading: boolean;
}

export function usePermissions(): Permissions {
  const { workspace, isLoading } = useCurrentWorkspace();
  const role = workspace?.role;
  return {
    isOwner: role === "owner",
    isMember: role === "member",
    isViewer: role === "viewer",
    canWrite: role === "owner" || role === "member",
    canManageMembers: role === "owner",
    isLoading,
  };
}
