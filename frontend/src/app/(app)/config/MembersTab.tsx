"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  listMembers,
  createMember,
  updateMember,
  deleteMember,
  createBankAccount,
  deleteBankAccount,
  getWorkspaceSettings,
  updateWorkspaceSettings,
  type FamilyMemberConfig,
  type BankAccountConfig,
  ApiError,
} from "@/lib/api";
import { bankLabel } from "@/lib/format";
import { Spinner } from "@/components/Spinner";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Trash2, Plus, Check, X } from "lucide-react";

const ROLES = [
  { value: "titular", label: "Titular" },
  { value: "conjuge", label: "Cônjuge" },
  { value: "filho", label: "Filho(a)" },
  { value: "dependente", label: "Dependente" },
];

export default function MembersTab() {
  const [members, setMembers] = useState<FamilyMemberConfig[]>([]);
  const [familySurname, setFamilySurname] = useState<string>("");
  const [familySurnameDirty, setFamilySurnameDirty] = useState(false);
  const [savingSurname, setSavingSurname] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<FamilyMemberConfig | null>(null);
  const [deleteAccountTarget, setDeleteAccountTarget] = useState<{ memberId: string; acc: BankAccountConfig } | null>(null);

  const reload = useCallback(async () => {
    try {
      const [data, ws] = await Promise.all([listMembers(), getWorkspaceSettings()]);
      setMembers(data.members);
      setFamilySurname(ws.family_surname ?? "");
      setFamilySurnameDirty(false);
    } catch {
      setError("Erro ao carregar dados do workspace");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { reload(); }, [reload]);

  async function handleSaveSurname() {
    setError(""); setSuccess("");
    setSavingSurname(true);
    try {
      const updated = await updateWorkspaceSettings({ family_surname: familySurname.trim() || null });
      setFamilySurname(updated.family_surname ?? "");
      setFamilySurnameDirty(false);
      setSuccess("Sobrenome da família atualizado!");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao salvar sobrenome");
    } finally {
      setSavingSurname(false);
    }
  }

  async function handleCreate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(""); setSuccess("");
    const fd = new FormData(e.currentTarget);
    try {
      await createMember({
        key: fd.get("key") as string,
        full_name: fd.get("full_name") as string,
        short_name: fd.get("short_name") as string,
        cpf: (fd.get("cpf") as string) || undefined,
        birth_date: (fd.get("birth_date") as string) || undefined,
        role: fd.get("role") as string,
        order: members.length,
      });
      setSuccess("Membro adicionado!");
      setShowAdd(false);
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao adicionar membro");
    }
  }

  async function handleDelete() {
    if (!deleteTarget?.id) return;
    try {
      await deleteMember(deleteTarget.id);
      await reload();
    } catch { setError("Erro ao remover membro"); }
    setDeleteTarget(null);
  }

  async function handleUpdate(m: FamilyMemberConfig, field: string, value: string) {
    if (!m.id) return;
    try {
      await updateMember(m.id, { [field]: value || null });
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao atualizar");
    }
  }

  async function handleAddAccount(memberId: string, e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    const fd = new FormData(e.currentTarget);
    try {
      await createBankAccount(memberId, {
        institution_code: fd.get("institution_code") as string,
        account_type: fd.get("account_type") as string,
        agency: (fd.get("agency") as string) || undefined,
        account_number: (fd.get("account_number") as string) || undefined,
      });
      e.currentTarget.reset();
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao adicionar conta");
    }
  }

  async function handleDeleteAccount() {
    if (!deleteAccountTarget) return;
    try {
      await deleteBankAccount(deleteAccountTarget.memberId, deleteAccountTarget.acc.id!);
      await reload();
    } catch { setError("Erro ao remover conta"); }
    setDeleteAccountTarget(null);
  }

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div>
      {/* Messages */}
      {error && (
        <div className="mb-4 rounded-lg bg-loss/10 p-3 text-sm text-loss">
          {error} <button onClick={() => setError("")} className="ml-2 underline">fechar</button>
        </div>
      )}
      {success && (
        <div className="mb-4 rounded-lg bg-gain/10 p-3 text-sm text-gain">
          {success} <button onClick={() => setSuccess("")} className="ml-2 underline">fechar</button>
        </div>
      )}

      {/* Workspace settings — Sobrenome da família (vai para a capa do relatório) */}
      <Card className="mb-4">
        <CardContent className="p-5">
          <Label htmlFor="family-surname" className="mb-1 block text-sm font-medium">
            Sobrenome da família
          </Label>
          <p className="mb-3 text-xs text-muted-foreground">
            Aparece na capa do relatório (ex: &quot;Relatório Financeiro Família Silva&quot;) e no nome do arquivo HTML gerado.
          </p>
          <div className="flex gap-2">
            <Input
              id="family-surname"
              value={familySurname}
              onChange={(e) => { setFamilySurname(e.target.value); setFamilySurnameDirty(true); }}
              placeholder="ex: Silva, Ferreira Campos"
              maxLength={255}
              className="flex-1"
            />
            <Button
              onClick={handleSaveSurname}
              disabled={!familySurnameDirty || savingSurname}
            >
              {savingSurname ? "Salvando..." : "Salvar"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Member Cards */}
      <div className="space-y-3">
        {members.map((m) => (
          <Card key={m.id ?? m.key}>
            <CardContent className="p-0">
              <div className="flex items-center gap-4 px-5 py-4">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-sm font-medium text-primary">
                  {m.short_name.charAt(0).toUpperCase()}
                </div>
                <div className="flex-1">
                  <p className="font-medium">{m.full_name}</p>
                  <p className="text-xs text-muted-foreground">
                    {ROLES.find((r) => r.value === m.role)?.label ?? m.role}
                    {m.cpf && ` · CPF: ***${m.cpf.slice(-4)}`}
                    {m.birth_date && ` · Nasc: ${m.birth_date}`}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">{m.accounts.length} conta(s)</span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setExpandedId(expandedId === m.id ? null : m.id ?? null)}
                  >
                    {expandedId === m.id ? "Fechar" : "Editar"}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-muted-foreground hover:text-destructive"
                    onClick={() => setDeleteTarget(m)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>

              {/* Expanded Edit Section */}
              {expandedId === m.id && m.id && (
                <div className="border-t border-border px-5 py-4 space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <InlineField label="Nome completo" value={m.full_name} onSave={(v) => handleUpdate(m, "full_name", v)} />
                    <InlineField label="Nome curto" value={m.short_name} onSave={(v) => handleUpdate(m, "short_name", v)} />
                    <InlineField label="CPF" value={m.cpf ?? ""} onSave={(v) => handleUpdate(m, "cpf", v)} placeholder="00000000000" />
                    <InlineField label="Nascimento" value={m.birth_date ?? ""} onSave={(v) => handleUpdate(m, "birth_date", v)} type="date" />
                    <div>
                      <Label className="mb-1 text-xs text-muted-foreground">Papel</Label>
                      <select
                        value={m.role}
                        onChange={(e) => handleUpdate(m, "role", e.target.value)}
                        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                      >
                        {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                      </select>
                    </div>
                  </div>

                  {/* Bank Accounts */}
                  <div>
                    <h4 className="mb-2 text-xs font-medium text-muted-foreground uppercase">Contas Bancárias</h4>
                    {m.accounts.length > 0 && (
                      <div className="mb-2 space-y-1">
                        {m.accounts.map((acc) => (
                          <div key={acc.id} className="flex items-center justify-between rounded-lg bg-muted px-3 py-2 text-sm">
                            <span>
                              <strong>{bankLabel(acc.institution_code)}</strong>
                              <span className="ml-2 text-muted-foreground">{acc.account_type}</span>
                              {acc.agency && <span className="ml-2 text-muted-foreground">Ag: {acc.agency}</span>}
                              {acc.account_number && <span className="ml-1 text-muted-foreground">Cc: {acc.account_number}</span>}
                            </span>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-muted-foreground hover:text-destructive"
                              onClick={() => setDeleteAccountTarget({ memberId: m.id!, acc })}
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    )}
                    <form onSubmit={(e) => handleAddAccount(m.id!, e)} className="flex gap-2">
                      <Input name="institution_code" placeholder="Banco (ex: itau)" required className="w-28 text-xs" />
                      <Input name="account_type" placeholder="Tipo (ex: extratoconta)" required className="w-36 text-xs" />
                      <Input name="agency" placeholder="Agência" className="w-20 text-xs" />
                      <Input name="account_number" placeholder="Conta" className="w-24 text-xs" />
                      <Button type="submit" size="sm">
                        <Plus className="h-3.5 w-3.5" />
                      </Button>
                    </form>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Add Member Form */}
      {showAdd ? (
        <form onSubmit={handleCreate} className="mt-4 rounded-xl border border-primary/30 bg-primary/5 p-5 space-y-3">
          <h3 className="font-medium">Novo Membro</h3>
          <div className="grid grid-cols-2 gap-3">
            <Input name="key" placeholder="Key (ex: david)" required />
            <Input name="full_name" placeholder="Nome completo" required />
            <Input name="short_name" placeholder="Nome curto" required />
            <Input name="cpf" placeholder="CPF (11 dígitos)" />
            <Input name="birth_date" type="date" />
            <select name="role" required className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring">
              {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
            </select>
          </div>
          <div className="flex gap-2">
            <Button type="submit">Salvar</Button>
            <Button type="button" variant="outline" onClick={() => setShowAdd(false)}>Cancelar</Button>
          </div>
        </form>
      ) : (
        <Button variant="outline" className="mt-4 w-full border-dashed" onClick={() => setShowAdd(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Adicionar membro
        </Button>
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title={`Remover "${deleteTarget?.full_name}"?`}
        description="Todas as contas vinculadas serão removidas."
        confirmLabel="Remover"
        variant="destructive"
        onConfirm={handleDelete}
      />

      <ConfirmDialog
        open={!!deleteAccountTarget}
        onOpenChange={(open) => !open && setDeleteAccountTarget(null)}
        title={`Remover conta ${deleteAccountTarget ? bankLabel(deleteAccountTarget.acc.institution_code) : ""}?`}
        confirmLabel="Remover"
        variant="destructive"
        onConfirm={handleDeleteAccount}
      />
    </div>
  );
}

function InlineField({ label, value, onSave, placeholder, type = "text" }: {
  label: string; value: string; onSave: (v: string) => void; placeholder?: string; type?: string;
}) {
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState(value);

  if (!editing) {
    return (
      <div>
        <Label className="mb-1 text-xs text-muted-foreground">{label}</Label>
        <button onClick={() => setEditing(true)} className="w-full text-left rounded-lg border border-transparent px-2 py-1.5 text-sm hover:border-border hover:bg-accent">
          {value || <span className="text-muted-foreground">{placeholder ?? "—"}</span>}
        </button>
      </div>
    );
  }

  return (
    <div>
      <Label className="mb-1 text-xs text-muted-foreground">{label}</Label>
      <div className="flex gap-1">
        <Input
          type={type}
          value={val}
          onChange={(e) => setVal(e.target.value)}
          placeholder={placeholder}
          autoFocus
          className="flex-1"
        />
        <Button size="sm" onClick={() => { onSave(val); setEditing(false); }}>
          <Check className="h-3.5 w-3.5" />
        </Button>
        <Button size="sm" variant="outline" onClick={() => { setVal(value); setEditing(false); }}>
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}
