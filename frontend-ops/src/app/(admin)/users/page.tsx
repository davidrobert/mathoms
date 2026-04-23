"use client";

import { useCallback, useEffect, useState } from "react";
import { Badge, Button, TextInput } from "@/components/ui";
import { api, AdminApiError } from "@/lib/api";
import { useAuthGuard } from "@/lib/auth-guard";
import type { AdminUserSummary } from "@/lib/types";
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

export default function UsersPage() {
  const { principal } = useAuthGuard();
  const [users, setUsers] = useState<AdminUserSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openAction, setOpenAction] = useState<OpenAction | null>(null);

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
              <th className="text-left px-4 py-2 font-medium">E-mail</th>
              <th className="text-left px-4 py-2 font-medium">Nome</th>
              <th className="text-left px-4 py-2 font-medium">Status</th>
              <th className="text-left px-4 py-2 font-medium">Dev</th>
              <th className="text-right px-4 py-2 font-medium">Ações</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-surface-muted-fg">
                  Carregando…
                </td>
              </tr>
            )}
            {!loading && users.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-surface-muted-fg">
                  Nenhum usuário encontrado.
                </td>
              </tr>
            )}
            {users.map((u) => (
              <tr key={u.id} className="border-t border-surface-border">
                <td className="px-4 py-2">
                  <span className="text-surface-fg">{u.email}</span>
                </td>
                <td className="px-4 py-2 text-surface-muted-fg">{u.full_name}</td>
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
