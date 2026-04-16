"use client";

/**
 * AcessosTab — gestão de pessoas com acesso ao workspace (F9).
 *
 * Diferente do `MembersTab` (que lista `FamilyMember` — pessoas físicas
 * da família com CPFs), esta aba gerencia `WorkspaceMember` — usuários
 * logados que compartilham acesso à conta.
 *
 * Owner-only pode convidar/remover/mudar roles. Outros membros veem a
 * listagem (transparência sobre quem mais tem acesso), mas as ações
 * ficam desabilitadas.
 *
 * Convite sem email (F9.1): backend devolve `token` + `invite_path`; UI
 * mostra o link copiável. Owner envia manualmente (WhatsApp, SMS, etc).
 */

import { FormEvent, useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api";
import type {
  InvitableRole,
  InvitationCreateResponse,
  InvitationResponse,
  WorkspaceMemberResponse,
} from "@/lib/api";
import {
  createWorkspaceInvitation,
  listWorkspaceInvitations,
  listWorkspaceMembers,
  removeWorkspaceMember,
  revokeWorkspaceInvitation,
  updateMemberRole,
} from "@/lib/api";
import { roleLabel, ROLE_COLOR_CLASSES, roleDescription } from "@/lib/roleLabels";
import { useCurrentUser } from "@/lib/useCurrentUser";
import { useCurrentWorkspace } from "@/lib/useCurrentWorkspace";

import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Spinner } from "@/components/Spinner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Copy, Trash2, UserPlus, X } from "lucide-react";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function RoleBadge({ role }: { role: "owner" | "member" | "viewer" }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${ROLE_COLOR_CLASSES[role]}`}
      title={roleDescription(role)}
    >
      {roleLabel(role)}
    </span>
  );
}

export default function AcessosTab() {
  const { workspace, isLoading: workspaceLoading } = useCurrentWorkspace();
  const { user: currentUser } = useCurrentUser();
  const [members, setMembers] = useState<WorkspaceMemberResponse[]>([]);
  const [invitations, setInvitations] = useState<InvitationResponse[]>([]);
  const [loading, setLoading] = useState(true);

  // Form state — convite
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<InvitableRole>("viewer");
  const [inviting, setInviting] = useState(false);
  const [createdInvite, setCreatedInvite] =
    useState<InvitationCreateResponse | null>(null);

  // Dialogs
  const [removeTarget, setRemoveTarget] =
    useState<WorkspaceMemberResponse | null>(null);
  const [revokeTarget, setRevokeTarget] = useState<InvitationResponse | null>(
    null
  );

  const reload = useCallback(async () => {
    if (!workspace) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const [m, inv] = await Promise.all([
        listWorkspaceMembers(workspace.id),
        listWorkspaceInvitations(workspace.id),
      ]);
      setMembers(m.members);
      setInvitations(inv.invitations);
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.message : "Erro ao carregar acessos"
      );
    } finally {
      setLoading(false);
    }
  }, [workspace]);

  useEffect(() => {
    reload();
  }, [reload]);

  const isOwner = workspace?.role === "owner";

  async function handleInvite(e: FormEvent) {
    e.preventDefault();
    if (!workspace) return;
    setInviting(true);
    try {
      const result = await createWorkspaceInvitation(
        workspace.id,
        inviteEmail.trim(),
        inviteRole
      );
      setCreatedInvite(result);
      setInviteEmail("");
      await reload();
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.message : "Erro ao criar convite"
      );
    } finally {
      setInviting(false);
    }
  }

  async function handleChangeRole(
    member: WorkspaceMemberResponse,
    newRole: InvitableRole
  ) {
    if (!workspace) return;
    try {
      await updateMemberRole(workspace.id, member.user_id, newRole);
      toast.success(`Papel de ${member.full_name} atualizado.`);
      await reload();
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.message : "Erro ao atualizar papel"
      );
    }
  }

  async function handleRemove() {
    if (!workspace || !removeTarget) return;
    try {
      await removeWorkspaceMember(workspace.id, removeTarget.user_id);
      toast.success(`${removeTarget.full_name} removido do workspace.`);
      setRemoveTarget(null);
      await reload();
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.message : "Erro ao remover membro"
      );
    }
  }

  async function handleRevoke() {
    if (!workspace || !revokeTarget) return;
    try {
      await revokeWorkspaceInvitation(workspace.id, revokeTarget.id);
      toast.success("Convite cancelado.");
      setRevokeTarget(null);
      await reload();
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.message : "Erro ao cancelar convite"
      );
    }
  }

  async function copyInviteLink() {
    if (!createdInvite) return;
    const url = `${window.location.origin}${createdInvite.invite_path}`;
    try {
      await navigator.clipboard.writeText(url);
      toast.success("Link copiado. Envie ao convidado.");
    } catch {
      toast.error("Não foi possível copiar. Selecione o link manualmente.");
    }
  }

  if (workspaceLoading || loading) {
    return (
      <div className="flex h-40 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  if (!workspace) {
    return (
      <div className="text-sm text-muted-foreground">
        Nenhum workspace carregado.
      </div>
    );
  }

  const pendingInvites = invitations.filter((i) => i.status === "pending");
  const pastInvites = invitations.filter((i) => i.status !== "pending");

  return (
    <div className="space-y-8">
      {/* ─── Convidar ─────────────────────────────── */}
      {isOwner && (
        <Card>
          <CardContent className="space-y-4 pt-6">
            <div>
              <h3 className="text-base font-semibold">Convidar alguém</h3>
              <p className="mt-1 text-xs text-muted-foreground">
                Os dados financeiros da sua família são sensíveis.
                Escolha com cuidado o papel — você pode mudar ou remover
                o acesso depois.
              </p>
            </div>

            <form onSubmit={handleInvite} className="grid gap-3 sm:grid-cols-[1fr_200px_auto]">
              <div>
                <Label htmlFor="invite-email">Email</Label>
                <Input
                  id="invite-email"
                  type="email"
                  required
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="pessoa@exemplo.com"
                />
              </div>
              <div>
                <Label htmlFor="invite-role">Papel</Label>
                <Select
                  value={inviteRole}
                  onValueChange={(v) => setInviteRole(v as InvitableRole)}
                >
                  <SelectTrigger id="invite-role">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="viewer">
                      Acompanha (só visualiza)
                    </SelectItem>
                    <SelectItem value="member">
                      Coadministrador (edita)
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-end">
                <Button type="submit" disabled={inviting || !inviteEmail}>
                  <UserPlus className="mr-2 h-4 w-4" />
                  {inviting ? "Criando..." : "Convidar"}
                </Button>
              </div>
            </form>

            {createdInvite && (
              <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm dark:border-amber-900 dark:bg-amber-950">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <p className="font-medium">
                      Convite criado para {createdInvite.invitation.email}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Envie o link abaixo por WhatsApp, SMS ou pessoalmente.
                      Este é o único momento em que o link fica visível — se
                      perder, crie um novo convite.
                    </p>
                    <code className="mt-2 block break-all rounded bg-background px-2 py-1 text-xs">
                      {window.location.origin}
                      {createdInvite.invite_path}
                    </code>
                  </div>
                  <div className="flex flex-col gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={copyInviteLink}
                    >
                      <Copy className="mr-2 h-3.5 w-3.5" />
                      Copiar link
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setCreatedInvite(null)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ─── Membros atuais ───────────────────────── */}
      <div>
        <div className="mb-3 flex items-baseline justify-between">
          <h3 className="text-base font-semibold">Pessoas com acesso</h3>
          <span className="text-xs text-muted-foreground">
            {members.length} {members.length === 1 ? "pessoa" : "pessoas"}
          </span>
        </div>

        <div className="divide-y rounded-md border">
          {members.map((m) => {
            const isSelf = currentUser?.id === m.user_id;
            const canModify = isOwner && m.role !== "owner" && !isSelf;
            return (
              <div
                key={m.user_id}
                className="flex items-center justify-between gap-4 px-4 py-3"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium truncate">{m.full_name}</span>
                    {isSelf && (
                      <span className="text-xs text-muted-foreground">
                        (você)
                      </span>
                    )}
                    <RoleBadge role={m.role} />
                  </div>
                  <div className="text-xs text-muted-foreground truncate">
                    {m.email} • entrou em {formatDate(m.joined_at)}
                  </div>
                </div>
                {canModify && (
                  <div className="flex items-center gap-2">
                    <Select
                      value={m.role}
                      onValueChange={(v) =>
                        handleChangeRole(m, v as InvitableRole)
                      }
                    >
                      <SelectTrigger className="h-8 w-[180px] text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="member">
                          Coadministrador
                        </SelectItem>
                        <SelectItem value="viewer">Acompanha</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setRemoveTarget(m)}
                      aria-label={`Remover ${m.full_name}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* ─── Convites pendentes ────────────────── */}
      {isOwner && pendingInvites.length > 0 && (
        <div>
          <h3 className="mb-3 text-base font-semibold">Convites pendentes</h3>
          <div className="divide-y rounded-md border">
            {pendingInvites.map((i) => (
              <div
                key={i.id}
                className="flex items-center justify-between gap-4 px-4 py-3"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium truncate">{i.email}</span>
                    <RoleBadge role={i.role} />
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Expira em {formatDate(i.expires_at)}
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setRevokeTarget(i)}
                >
                  <X className="mr-2 h-3.5 w-3.5" />
                  Cancelar
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ─── Histórico de convites ─────────── */}
      {isOwner && pastInvites.length > 0 && (
        <details className="text-sm">
          <summary className="cursor-pointer text-muted-foreground">
            Histórico de convites ({pastInvites.length})
          </summary>
          <div className="mt-3 divide-y rounded-md border">
            {pastInvites.map((i) => (
              <div
                key={i.id}
                className="flex items-center justify-between px-4 py-2 text-xs"
              >
                <div>
                  <span className="font-medium">{i.email}</span>
                  <span className="ml-2 text-muted-foreground">
                    ({roleLabel(i.role)})
                  </span>
                </div>
                <span className="text-muted-foreground">
                  {
                    {
                      accepted: `Aceito em ${
                        i.accepted_at ? formatDate(i.accepted_at) : "—"
                      }`,
                      revoked: `Cancelado em ${
                        i.revoked_at ? formatDate(i.revoked_at) : "—"
                      }`,
                      expired: "Expirado",
                      pending: "Pendente",
                    }[i.status]
                  }
                </span>
              </div>
            ))}
          </div>
        </details>
      )}

      {/* ─── Confirmações ────────────────────── */}
      <ConfirmDialog
        open={!!removeTarget}
        onOpenChange={(open) => !open && setRemoveTarget(null)}
        title="Remover acesso?"
        description={
          removeTarget
            ? `${removeTarget.full_name} perde o acesso imediatamente. Você pode convidar de novo depois, mas eventos passados continuam no histórico.`
            : ""
        }
        confirmLabel="Remover"
        variant="destructive"
        onConfirm={handleRemove}
      />

      <ConfirmDialog
        open={!!revokeTarget}
        onOpenChange={(open) => !open && setRevokeTarget(null)}
        title="Cancelar convite?"
        description={
          revokeTarget
            ? `O convite para ${revokeTarget.email} ficará inválido. Se precisar, crie um novo depois.`
            : ""
        }
        confirmLabel="Cancelar convite"
        variant="destructive"
        onConfirm={handleRevoke}
      />
    </div>
  );
}
