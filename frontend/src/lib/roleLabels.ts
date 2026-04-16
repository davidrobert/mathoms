/** Traduções humanas dos roles técnicos de workspace (F9).
 *
 * A convenção de nomenclatura foi definida no conselho de produto
 * (ADR-072/F9): labels em PT-BR que refletem a relação familiar, não a
 * hierarquia SaaS típica.
 */

import type { WorkspaceRole } from "./api";

export const ROLE_LABELS: Record<WorkspaceRole, string> = {
  owner: "Responsável",
  member: "Coadministrador",
  viewer: "Acompanha",
};

export const ROLE_DESCRIPTIONS: Record<WorkspaceRole, string> = {
  owner:
    "Criou a conta. Pode gerenciar membros e deletar o workspace.",
  member:
    "Pode editar metas, lançar transações e importar documentos. " +
    "Não pode remover outros membros.",
  viewer:
    "Pode visualizar tudo, mas não edita metas nem lança transações.",
};

export const ROLE_COLOR_CLASSES: Record<WorkspaceRole, string> = {
  owner:
    "bg-amber-50 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300",
  member:
    "bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300",
  viewer:
    "bg-gray-100 text-gray-600 dark:bg-gray-800/50 dark:text-gray-400",
};

export function roleLabel(role: WorkspaceRole): string {
  return ROLE_LABELS[role];
}

export function roleDescription(role: WorkspaceRole): string {
  return ROLE_DESCRIPTIONS[role];
}
