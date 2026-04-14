"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  listVaultPasswords,
  createVaultPassword,
  deleteVaultPassword,
  retryUnlock,
  type VaultPasswordResponse,
  ApiError,
} from "@/lib/api";
import { formatDate } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import { Spinner } from "@/components/Spinner";
import { EmptyState } from "@/components/EmptyState";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Trash2, KeyRound } from "lucide-react";

export default function VaultPage() {
  const [passwords, setPasswords] = useState<VaultPasswordResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [label, setLabel] = useState("");
  const [password, setPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; label: string } | null>(null);

  const reload = useCallback(async () => {
    try {
      const data = await listVaultPasswords();
      setPasswords(data.passwords);
    } catch {
      setError("Erro ao carregar senhas");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSuccessMsg("");
    setSaving(true);
    try {
      await createVaultPassword(label, password);
      setLabel("");
      setPassword("");
      setSuccessMsg("Senha adicionada!");
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao adicionar senha");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    try {
      await deleteVaultPassword(deleteTarget.id);
      setPasswords((prev) => prev.filter((p) => p.id !== deleteTarget.id));
    } catch {
      setError("Erro ao remover senha");
    } finally {
      setDeleteTarget(null);
    }
  }

  async function handleRetryUnlock() {
    setError("");
    try {
      const result = await retryUnlock();
      const unlocked = result.filter((d) => d.status === "ready").length;
      setSuccessMsg(
        unlocked > 0
          ? `${unlocked} documento(s) desbloqueado(s)!`
          : "Nenhum documento conseguiu ser desbloqueado com as senhas atuais."
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao tentar desbloquear");
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <PageHeader
        title="Vault de Senhas"
        description="Senhas usadas para desbloquear PDFs protegidos. Armazenadas de forma criptografada."
      />

      {error && (
        <div className="mb-4 rounded-lg bg-loss/10 p-3 text-sm text-loss">
          {error}
          <button onClick={() => setError("")} className="ml-2 font-medium underline">fechar</button>
        </div>
      )}
      {successMsg && (
        <div className="mb-4 rounded-lg bg-gain/10 p-3 text-sm text-gain">
          {successMsg}
          <button onClick={() => setSuccessMsg("")} className="ml-2 font-medium underline">fechar</button>
        </div>
      )}

      {/* Add Form */}
      <Card className="mb-6">
        <CardContent>
          <h2 className="mb-4 text-sm font-medium text-muted-foreground">Adicionar senha</h2>
          <form onSubmit={handleAdd} className="flex gap-3">
            <Input
              type="text"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="Rótulo (ex: Itaú IRPF)"
              required
              className="flex-1"
            />
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Senha"
              required
              className="w-48"
            />
            <Button type="submit" disabled={saving}>
              {saving ? "Salvando..." : "Adicionar"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Passwords List */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Spinner size="lg" />
        </div>
      ) : passwords.length === 0 ? (
        <EmptyState
          variant="no-data"
          icon={KeyRound}
          title="Nenhuma senha cadastrada."
          description="Adicione senhas de PDFs protegidos para desbloqueio automático no upload."
        />
      ) : (
        <div className="space-y-2">
          {passwords.map((pw) => (
            <div
              key={pw.id}
              className="flex items-center justify-between rounded-lg border border-border bg-card px-4 py-3"
            >
              <div>
                <p className="text-sm font-medium">{pw.label}</p>
                <p className="text-xs text-muted-foreground">Adicionada em {formatDate(pw.created_at)}</p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setDeleteTarget({ id: pw.id, label: pw.label })}
                className="text-muted-foreground hover:text-destructive"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="mt-6 flex gap-3">
        <Button variant="outline" onClick={handleRetryUnlock}>
          Tentar desbloquear documentos pendentes
        </Button>
        <Button variant="outline" nativeButton={false} render={<Link href="/documents" />}>
          Ver documentos
        </Button>
      </div>

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title={`Remover senha "${deleteTarget?.label}"?`}
        description="A senha será removida permanentemente."
        confirmLabel="Remover"
        variant="destructive"
        onConfirm={handleDelete}
      />
    </div>
  );
}
