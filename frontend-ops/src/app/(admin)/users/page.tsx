"use client";

import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import { Badge, Button, TextInput } from "@/components/ui";
import { api, AdminApiError } from "@/lib/api";
import { useAuthGuard } from "@/lib/auth-guard";
import type { AdminUserSummary, UserWorkspace } from "@/lib/types";
import { UserActionModal } from "./user-actions";

type ActionKind =
  | "anonymize"
  | "hard_delete"
  | "reset_password"
  | "edit_profile"
  | "edit_email";

interface OpenAction {
  user: AdminUserSummary;
  kind: ActionKind;
}

type SortKey = "email" | "full_name" | "id" | "is_active" | "is_developer";
type SortDirection = "asc" | "desc";

interface SortState {
  key: SortKey;
  direction: SortDirection;
}

function compareUsers(a: AdminUserSummary, b: AdminUserSummary, key: SortKey): number {
  const av = a[key];
  const bv = b[key];
  if (typeof av === "boolean" && typeof bv === "boolean") {
    return av === bv ? 0 : av ? -1 : 1;
  }
  return String(av).localeCompare(String(bv), "pt-BR", { sensitivity: "base" });
}

export default function UsersPage() {
  const { principal } = useAuthGuard();
  const [users, setUsers] = useState<AdminUserSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openAction, setOpenAction] = useState<OpenAction | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [expandedUserId, setExpandedUserId] = useState<string | null>(null);
  const [workspacesByUser, setWorkspacesByUser] = useState<
    Record<string, UserWorkspace[] | "loading" | "error">
  >({});
  const [sort, setSort] = useState<SortState | null>(null);

  function toggleSort(key: SortKey): void {
    setSort((prev) => {
      if (!prev || prev.key !== key) return { key, direction: "asc" };
      if (prev.direction === "asc") return { key, direction: "desc" };
      return null;
    });
  }

  const sortedUsers = useMemo(() => {
    if (!sort) return users;
    const factor = sort.direction === "asc" ? 1 : -1;
    return [...users].sort((a, b) => compareUsers(a, b, sort.key) * factor);
  }, [users, sort]);

  async function copyId(id: string): Promise<void> {
    await navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  }

  async function toggleExpand(userId: string): Promise<void> {
    if (expandedUserId === userId) {
      setExpandedUserId(null);
      return;
    }
    setExpandedUserId(userId);
    if (workspacesByUser[userId] !== undefined && workspacesByUser[userId] !== "error") return;
    setWorkspacesByUser((prev) => ({ ...prev, [userId]: "loading" }));
    try {
      const res = await api.listUserWorkspaces(userId);
      setWorkspacesByUser((prev) => ({ ...prev, [userId]: res.workspaces }));
    } catch {
      setWorkspacesByUser((prev) => ({ ...prev, [userId]: "error" }));
    }
  }

  const load = useCallback(
    async (filter: string): Promise<void> => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.listUsers({ q: filter || undefined, limit: 200 });
        setUsers(res.users);
        setTotal(res.total);
      } catch (err) {
        if (err instanceof AdminApiError) setError(`${err.status} · ${err.code}`);
        else setError("Falha ao carregar usuários.");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    void load("");
  }, [load]);

  async function toggleDev(u: AdminUserSummary): Promise<void> {
    const enabling = !u.is_developer;
    if (enabling) {
      const ok = window.confirm(
        `Ligar flag developer para ${u.email}? ` +
          "Permite acesso a endpoints /dev/* e sessões existentes serão invalidadas.",
      );
      if (!ok) return;
    }
    try {
      await api.setDeveloperFlag(u.id, enabling);
      await load(q);
    } catch (err) {
      setError(err instanceof AdminApiError ? `${err.status} · ${err.code}` : "Falha ao alternar flag.");
    }
  }

  const canHardDelete = principal?.role === "superadmin";

  return (
    <section>
      <div className="flex items-end justify-between gap-4 mb-6">
        <div>
          <h1 className="font-display text-2xl font-semibold text-surface-fg">
            Usuários
          </h1>
          <p className="text-sm text-surface-muted-fg">
            Total: {total.toLocaleString("pt-BR")} · exibindo {users.length}
          </p>
        </div>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            void load(q);
          }}
        >
          <TextInput
            placeholder="Filtrar por email ou nome"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="w-64"
          />
          <Button variant="secondary" type="submit">Buscar</Button>
        </form>
      </div>

      {error && (
        <div className="mb-4 rounded-md border border-brand-danger/30 bg-brand-danger/10 text-brand-danger text-sm px-3 py-2">
          {error}
        </div>
      )}

      <div className="overflow-x-auto border border-surface-border rounded-card bg-surface-card">
        <table className="w-full text-sm">
          <thead className="bg-surface-muted text-surface-muted-fg">
            <tr>
              <SortableHeader label="E-mail" sortKey="email" sort={sort} onToggle={toggleSort} />
              <SortableHeader label="Nome" sortKey="full_name" sort={sort} onToggle={toggleSort} />
              <SortableHeader label="ID" sortKey="id" sort={sort} onToggle={toggleSort} />
              <SortableHeader label="Status" sortKey="is_active" sort={sort} onToggle={toggleSort} />
              <SortableHeader label="Dev" sortKey="is_developer" sort={sort} onToggle={toggleSort} />
              <th className="text-right px-4 py-2 font-medium">Ações</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-surface-muted-fg">
                  Carregando…
                </td>
              </tr>
            )}
            {!loading && users.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-surface-muted-fg">
                  Nenhum usuário encontrado.
                </td>
              </tr>
            )}
            {sortedUsers.map((u) => (
              <Fragment key={u.id}>
              <tr className="border-t border-surface-border">
                <td className="px-4 py-2">
                  <button
                    type="button"
                    onClick={() => void toggleExpand(u.id)}
                    className="mr-2 text-surface-muted-fg hover:text-brand-primary"
                    title={expandedUserId === u.id ? "Ocultar workspaces" : "Ver workspaces"}
                  >
                    {expandedUserId === u.id ? "▾" : "▸"}
                  </button>
                  <span className="text-surface-fg">{u.email}</span>
                </td>
                <td className="px-4 py-2 text-surface-muted-fg">{u.full_name}</td>
                <td className="px-4 py-2">
                  <button
                    type="button"
                    onClick={() => void copyId(u.id)}
                    title="Copiar user_id"
                    className="font-mono text-xs text-surface-muted-fg hover:text-brand-primary hover:underline"
                  >
                    {copiedId === u.id ? "copiado ✓" : `${u.id.slice(0, 8)}…`}
                  </button>
                </td>
                <td className="px-4 py-2">
                  <Badge tone={u.is_active ? "success" : "neutral"}>
                    {u.is_active ? "ativo" : "inativo"}
                  </Badge>
                </td>
                <td className="px-4 py-2">
                  <label className="inline-flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={u.is_developer}
                      onChange={() => void toggleDev(u)}
                    />
                    <span className="text-xs text-surface-muted-fg">
                      {u.is_developer ? "sim" : "não"}
                    </span>
                  </label>
                </td>
                <td className="px-4 py-2">
                  <div className="flex justify-end gap-1">
                    <Button
                      variant="ghost"
                      onClick={() => setOpenAction({ user: u, kind: "edit_profile" })}
                    >
                      Editar
                    </Button>
                    <Button
                      variant="ghost"
                      onClick={() => setOpenAction({ user: u, kind: "edit_email" })}
                    >
                      E-mail
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => setOpenAction({ user: u, kind: "reset_password" })}
                    >
                      Reset pw
                    </Button>
                    <Button
                      variant="danger"
                      onClick={() => setOpenAction({ user: u, kind: "anonymize" })}
                    >
                      Anonimizar
                    </Button>
                    {canHardDelete && (
                      <Button
                        variant="danger"
                        title="Irreversível · quebra FKs em audit/pipeline. Use Anonimizar quando possível."
                        onClick={() => setOpenAction({ user: u, kind: "hard_delete" })}
                      >
                        Hard delete
                      </Button>
                    )}
                  </div>
                </td>
              </tr>
              {expandedUserId === u.id && (
                <tr className="bg-surface-muted">
                  <td colSpan={6} className="px-4 py-3">
                    <WorkspacesPanel entry={workspacesByUser[u.id]} onCopy={copyId} copiedId={copiedId} />
                  </td>
                </tr>
              )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {openAction && (
        <UserActionModal
          user={openAction.user}
          action={{ kind: openAction.kind }}
          canHardDelete={Boolean(canHardDelete)}
          onClose={() => setOpenAction(null)}
          onChanged={() => void load(q)}
        />
      )}
    </section>
  );
}

function SortableHeader({
  label,
  sortKey,
  sort,
  onToggle,
}: {
  label: string;
  sortKey: SortKey;
  sort: SortState | null;
  onToggle: (key: SortKey) => void;
}) {
  const active = sort?.key === sortKey;
  const indicator = active ? (sort.direction === "asc" ? "▲" : "▼") : "↕";
  const ariaSort = active ? (sort.direction === "asc" ? "ascending" : "descending") : "none";
  return (
    <th
      scope="col"
      aria-sort={ariaSort}
      className="text-left px-4 py-2 font-medium"
    >
      <button
        type="button"
        onClick={() => onToggle(sortKey)}
        className="inline-flex items-center gap-1 hover:text-brand-primary"
        title={`Ordenar por ${label}`}
      >
        <span>{label}</span>
        <span
          aria-hidden="true"
          className={active ? "text-brand-primary text-xs" : "text-surface-muted-fg/60 text-xs"}
        >
          {indicator}
        </span>
      </button>
    </th>
  );
}

function WorkspacesPanel({
  entry,
  onCopy,
  copiedId,
}: {
  entry: UserWorkspace[] | "loading" | "error" | undefined;
  onCopy: (id: string) => void | Promise<void>;
  copiedId: string | null;
}) {
  if (entry === undefined || entry === "loading") {
    return <span className="text-xs text-surface-muted-fg">Carregando workspaces…</span>;
  }
  if (entry === "error") {
    return <span className="text-xs text-brand-danger">Falha ao carregar.</span>;
  }
  if (entry.length === 0) {
    return <span className="text-xs text-surface-muted-fg">Nenhum workspace.</span>;
  }
  return (
    <div className="space-y-1">
      <div className="text-xs uppercase tracking-wide text-surface-muted-fg mb-1">
        {entry.length} workspace(s)
      </div>
      <ul className="space-y-1">
        {entry.map((ws) => (
          <li key={ws.id} className="flex items-center gap-3 text-sm">
            <button
              type="button"
              onClick={() => void onCopy(ws.id)}
              title="Copiar workspace_id"
              className="font-mono text-xs text-surface-muted-fg hover:text-brand-primary hover:underline"
            >
              {copiedId === ws.id ? "copiado ✓" : ws.id}
            </button>
            <span className="text-surface-fg">{ws.name}</span>
            <span className="text-xs text-surface-muted-fg">· {ws.role}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
