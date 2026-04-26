"use client";

import { ChevronsUpDown } from "lucide-react";
import { ROLE_COLOR_CLASSES, roleLabel } from "@/lib/roleLabels";
import { useCurrentWorkspace } from "@/lib/useCurrentWorkspace";
import type { UserWorkspace, WorkspaceRole } from "@/lib/api";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const STORAGE_KEY = "fin.currentWorkspaceId";

const sanitizeName = (name: string) => name.replace(/[!?]+$/, "").trim();

function RoleBadge({ role }: { role: WorkspaceRole }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider leading-none ${ROLE_COLOR_CLASSES[role]}`}
    >
      {roleLabel(role)}
    </span>
  );
}

function StaticCard({ workspace }: { workspace: UserWorkspace }) {
  return (
    <div className="flex flex-col gap-1.5 px-3 py-2.5">
      <span className="truncate text-sm font-semibold leading-tight">
        {sanitizeName(workspace.name)}
      </span>
      <RoleBadge role={workspace.role} />
    </div>
  );
}

function switchToWorkspace(currentId: string, id: string | null) {
  if (!id || id === currentId) return;
  window.localStorage.setItem(STORAGE_KEY, id);
  window.location.reload();
}

function SwitchableCard({
  workspace,
  workspaces,
}: {
  workspace: UserWorkspace;
  workspaces: UserWorkspace[];
}) {
  return (
    <Select value={workspace.id} onValueChange={(id) => switchToWorkspace(workspace.id, id)}>
      <SelectTrigger className="h-auto w-full justify-between rounded-lg border-none bg-transparent px-3 py-2.5 shadow-none hover:bg-accent focus:ring-0 [&>svg:last-child]:hidden">
        <SelectValue>
          <span className="flex flex-col gap-1.5 text-left">
            <span className="truncate text-sm font-semibold leading-tight max-w-[170px]">
              {sanitizeName(workspace.name)}
            </span>
            <RoleBadge role={workspace.role} />
          </span>
        </SelectValue>
        <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
      </SelectTrigger>
      <SelectContent align="start" className="w-[var(--radix-select-trigger-width)]">
        {workspaces.map((w) => (
          <SelectItem key={w.id} value={w.id}>
            <span className="inline-flex items-center gap-2">
              <span className="truncate max-w-[170px]">{sanitizeName(w.name)}</span>
              <RoleBadge role={w.role} />
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

export function SidebarWorkspaceCard() {
  const { workspace, workspaces, isLoading } = useCurrentWorkspace();
  if (isLoading || !workspace) return null;
  if (workspaces.length <= 1) return <StaticCard workspace={workspace} />;
  return <SwitchableCard workspace={workspace} workspaces={workspaces} />;
}
