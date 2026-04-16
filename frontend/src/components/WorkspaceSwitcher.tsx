"use client";

/**
 * WorkspaceSwitcher — seletor de workspace no header (F9 · débito #1).
 *
 *   - 0 workspaces: nada renderiza.
 *   - 1 workspace: mostra nome + badge de role, sem dropdown.
 *   - 2+ workspaces: Select; trocar persiste em localStorage e faz reload.
 *
 * Reload é deliberado — hooks de workspace só carregam no mount. Evolução
 * futura pode trocar por event bus / router.refresh() se a UX pedir.
 */

import { ROLE_COLOR_CLASSES, roleLabel } from "@/lib/roleLabels";
import { useCurrentWorkspace } from "@/lib/useCurrentWorkspace";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const STORAGE_KEY = "fin.currentWorkspaceId";

function RoleBadge({ role }: { role: "owner" | "member" | "viewer" }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider leading-none ${ROLE_COLOR_CLASSES[role]}`}
    >
      {roleLabel(role)}
    </span>
  );
}

export function WorkspaceSwitcher() {
  const { workspace, workspaces, isLoading } = useCurrentWorkspace();

  if (isLoading || !workspace) return null;

  const hasMultiple = workspaces.length > 1;

  if (!hasMultiple) {
    return (
      <div className="hidden items-center gap-2.5 sm:flex">
        <span className="text-style-heading-sm truncate max-w-[260px]">
          {workspace.name}
        </span>
        <RoleBadge role={workspace.role} />
      </div>
    );
  }

  function switchTo(id: string | null) {
    if (!id || id === workspace?.id) return;
    window.localStorage.setItem(STORAGE_KEY, id);
    window.location.reload();
  }

  return (
    <Select value={workspace.id} onValueChange={switchTo}>
      <SelectTrigger className="h-9 w-auto min-w-[200px] gap-2 border-none bg-transparent shadow-none focus:ring-0">
        <SelectValue>
          <span className="inline-flex items-center gap-2.5">
            <span className="text-style-heading-sm truncate max-w-[200px]">
              {workspace.name}
            </span>
            <RoleBadge role={workspace.role} />
          </span>
        </SelectValue>
      </SelectTrigger>
      <SelectContent align="start">
        {workspaces.map((w) => (
          <SelectItem key={w.id} value={w.id}>
            <span className="inline-flex items-center gap-2">
              <span className="truncate max-w-[200px]">{w.name}</span>
              <RoleBadge role={w.role} />
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
