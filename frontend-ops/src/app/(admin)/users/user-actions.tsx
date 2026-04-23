"use client";

import { useState } from "react";
import { Modal } from "@/components/Modal";
import { Button, TextInput } from "@/components/ui";
import { api, AdminApiError } from "@/lib/api";
import type { AdminUserSummary } from "@/lib/types";

type ActionKind =
  | { kind: "anonymize" }
  | { kind: "hard_delete" }
  | { kind: "reset_password" }
  | { kind: "edit_profile" }
  | { kind: "edit_email" };

interface Props {
  user: AdminUserSummary;
  action: ActionKind;
  canHardDelete: boolean;
  onClose: () => void;
  onChanged: () => void;
}

export function UserActionModal({ user, action, canHardDelete, onClose, onChanged }: Props) {
  if (action.kind === "anonymize") {
    return <AnonymizeModal user={user} onClose={onClose} onChanged={onChanged} />;
  }
  if (action.kind === "hard_delete") {
    if (!canHardDelete) {
      return (
        <Modal open title="Hard delete — permissão negada" onClose={onClose}>
          <p>Ação restrita ao papel <code>superadmin</code>.</p>
          <div className="pt-2 flex justify-end">
            <Button variant="secondary" onClick={onClose}>Fechar</Button>
          </div>
        </Modal>
      );
    }
    return <HardDeleteModal user={user} onClose={onClose} onChanged={onChanged} />;
  }
  if (action.kind === "reset_password") {
    return <ResetPasswordModal user={user} onClose={onClose} onChanged={onChanged} />;
  }
  if (action.kind === "edit_profile") {
    return <EditProfileModal user={user} onClose={onClose} onChanged={onChanged} />;
  }
  return <EditEmailModal user={user} onClose={onClose} onChanged={onChanged} />;
}

function formatError(err: unknown): string {
  if (err instanceof AdminApiError) return `${err.status} · ${err.code}`;
  return "Falha inesperada. Tente novamente.";
}

function AnonymizeModal({
  user,
  onClose,
  onChanged,
}: {
  user: AdminUserSummary;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function run(): Promise<void> {
    setError(null);
    setLoading(true);
    try {
      await api.anonymizeUser(user.id);
      onChanged();
      onClose();
    } catch (err) {
      setError(formatError(err));
      setLoading(false);
    }
  }

  return (
    <Modal
      open
      title="Anonimizar usuário"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button variant="danger" disabled={confirm !== "delete" || loading} onClick={run}>
            {loading ? "Processando…" : "Anonimizar"}
          </Button>
        </>
      }
    >
      <p>
        Você está prestes a <strong>anonimizar</strong>{" "}
        <code className="text-brand-primary">{user.email}</code>. FKs serão preservadas;
        usuário perderá acesso e dados pessoais serão substituídos.
      </p>
      <label className="block">
        <span className="text-sm">
          Digite <code>delete</code> para confirmar:
        </span>
        <TextInput
          className="mt-1 w-full"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          autoFocus
        />
      </label>
      {error && <p className="text-brand-danger text-sm">{error}</p>}
    </Modal>
  );
}

function HardDeleteModal({
  user,
  onClose,
  onChanged,
}: {
  user: AdminUserSummary;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [confirm, setConfirm] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const canSubmit = confirm === "hard_delete" && reason.trim().length >= 3 && !loading;

  async function run(): Promise<void> {
    setError(null);
    setLoading(true);
    try {
      await api.hardDeleteUser(user.id, reason.trim());
      onChanged();
      onClose();
    } catch (err) {
      setError(formatError(err));
      setLoading(false);
    }
  }

  return (
    <Modal
      open
      title="Hard delete — IRREVERSÍVEL"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button variant="danger" disabled={!canSubmit} onClick={run}>
            {loading ? "Processando…" : "Apagar definitivamente"}
          </Button>
        </>
      }
    >
      <p className="text-brand-danger">
        <strong>Ação irreversível.</strong> Apaga fisicamente o registro e quebra FKs.
        Prefira <em>anonimizar</em> na maioria dos casos.
      </p>
      <label className="block">
        <span className="text-sm">Motivo (mín. 3 caracteres):</span>
        <TextInput
          className="mt-1 w-full"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />
      </label>
      <label className="block">
        <span className="text-sm">
          Digite <code>hard_delete</code> para confirmar:
        </span>
        <TextInput
          className="mt-1 w-full"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
        />
      </label>
      {error && <p className="text-brand-danger text-sm">{error}</p>}
    </Modal>
  );
}

function ResetPasswordModal({
  user,
  onClose,
  onChanged,
}: {
  user: AdminUserSummary;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [tempPw, setTempPw] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  async function run(): Promise<void> {
    setError(null);
    setLoading(true);
    try {
      const res = await api.resetPassword(user.id);
      setTempPw(res.temp_password);
      onChanged();
    } catch (err) {
      setError(formatError(err));
    } finally {
      setLoading(false);
    }
  }

  async function copy(): Promise<void> {
    if (!tempPw) return;
    await navigator.clipboard.writeText(tempPw);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <Modal
      open
      title="Reset de senha"
      onClose={onClose}
      footer={
        tempPw ? (
          <Button variant="secondary" onClick={onClose}>Fechar</Button>
        ) : (
          <>
            <Button variant="secondary" onClick={onClose}>Cancelar</Button>
            <Button onClick={run} disabled={loading}>
              {loading ? "Gerando…" : "Gerar senha temporária"}
            </Button>
          </>
        )
      }
    >
      <p>
        Gera senha temporária para <code className="text-brand-primary">{user.email}</code>.
        A senha aparece uma única vez — copie e entregue por canal seguro.
      </p>
      {tempPw && (
        <div className="bg-surface-muted rounded-md p-3">
          <div className="text-xs text-surface-muted-fg mb-1">Senha temporária (exibida uma vez):</div>
          <div className="flex items-center justify-between gap-2">
            <code className="font-mono text-base text-surface-fg break-all">{tempPw}</code>
            <Button variant="secondary" onClick={copy}>
              {copied ? "Copiado" : "Copiar"}
            </Button>
          </div>
        </div>
      )}
      {error && <p className="text-brand-danger text-sm">{error}</p>}
    </Modal>
  );
}

function EditProfileModal({
  user,
  onClose,
  onChanged,
}: {
  user: AdminUserSummary;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [fullName, setFullName] = useState(user.full_name);
  const [isActive, setIsActive] = useState(user.is_active);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function run(): Promise<void> {
    setError(null);
    setLoading(true);
    try {
      const patch: { full_name?: string; is_active?: boolean } = {};
      if (fullName.trim() && fullName !== user.full_name) patch.full_name = fullName.trim();
      if (isActive !== user.is_active) patch.is_active = isActive;
      if (Object.keys(patch).length === 0) {
        onClose();
        return;
      }
      await api.updateUserProfile(user.id, patch);
      onChanged();
      onClose();
    } catch (err) {
      setError(formatError(err));
      setLoading(false);
    }
  }

  return (
    <Modal
      open
      title="Editar cadastro"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button onClick={run} disabled={loading}>
            {loading ? "Salvando…" : "Salvar"}
          </Button>
        </>
      }
    >
      <label className="block">
        <span className="text-sm">Nome completo</span>
        <TextInput
          className="mt-1 w-full"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
        />
      </label>
      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={isActive}
          onChange={(e) => setIsActive(e.target.checked)}
        />
        <span className="text-sm">Usuário ativo</span>
      </label>
      {error && <p className="text-brand-danger text-sm">{error}</p>}
    </Modal>
  );
}

function EditEmailModal({
  user,
  onClose,
  onChanged,
}: {
  user: AdminUserSummary;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [email, setEmail] = useState(user.email);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function run(): Promise<void> {
    setError(null);
    setLoading(true);
    try {
      if (email.trim() === user.email) {
        onClose();
        return;
      }
      await api.updateUserEmail(user.id, email.trim());
      onChanged();
      onClose();
    } catch (err) {
      if (err instanceof AdminApiError && err.status === 409) {
        setError("E-mail já está em uso por outro usuário.");
      } else {
        setError(formatError(err));
      }
      setLoading(false);
    }
  }

  return (
    <Modal
      open
      title="Alterar e-mail"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button onClick={run} disabled={loading}>
            {loading ? "Salvando…" : "Salvar"}
          </Button>
        </>
      }
    >
      <p className="text-sm text-surface-muted-fg">
        Mudar o e-mail invalida JWTs existentes do usuário (bump de token_version).
      </p>
      <label className="block">
        <span className="text-sm">Novo e-mail</span>
        <TextInput
          type="email"
          className="mt-1 w-full"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </label>
      {error && <p className="text-brand-danger text-sm">{error}</p>}
    </Modal>
  );
}
