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
import { useWorkspace } from "@/lib/WorkspaceProvider";

const ROLES = [
  { value: "titular", label: "Titular" },
  { value: "conjuge", label: "Cônjuge" },
  { value: "filho", label: "Filho(a)" },
  { value: "dependente", label: "Dependente" },
];

export default function MembersTab() {
  const { workspace } = useWorkspace();
  if (!workspace) return null;

  const [members, setMembers] = useState<FamilyMemberConfig[]>([]);
  const [familySurname, setFamilySurname] = useState<string>("");
  const [familySurnameDirty, setFamilySurnameDirty] = useState(false);
  const [savingSurname, setSavingSurname] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  /** Qual linha está expandida — usa `id` do banco ou, no fallback sem persistência, `key` (evita `null === null` em todos os cards). */
  const [expandedRowKey, setExpandedRowKey] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<FamilyMemberConfig | null>(null);
  const [deleteAccountTarget, setDeleteAccountTarget] = useState<{ memberId: string; acc: BankAccountConfig } | null>(null);

  const reload = useCallback(async () => {
    try {
      const [data, ws] = await Promise.all([listMembers(workspace!.id), getWorkspaceSettings(workspace!.id)]);
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
      const updated = await updateWorkspaceSettings(workspace!.id, { family_surname: familySurname.trim() || null });
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
      const created = await createMember(workspace!.id, {
        full_name: (fd.get("full_name") as string).trim(),
        short_name: (fd.get("short_name") as string).trim(),
        birth_name: ((fd.get("birth_name") as string) || "").trim() || undefined,
        cpf: (fd.get("cpf") as string) || undefined,
        birth_date: (fd.get("birth_date") as string) || undefined,
        role: fd.get("role") as string,
        order: members.length,
        key: ((fd.get("key") as string) || "").trim() || undefined,
      });
      setSuccess(
        "Membro adicionado. O cartão abaixo já está aberto — vincule as contas bancárias quando quiser.",
      );
      setShowAdd(false);
      setExpandedRowKey(created.id ?? created.key);
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao adicionar membro");
    }
  }

  async function handleDelete() {
    if (!deleteTarget?.id) return;
    try {
      await deleteMember(workspace!.id, deleteTarget.id);
      await reload();
    } catch { setError("Erro ao remover membro"); }
    setDeleteTarget(null);
  }

  async function handleUpdate(m: FamilyMemberConfig, field: string, value: string) {
    if (!m.id) return;
    try {
      await updateMember(workspace!.id, m.id, { [field]: value || null });
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
      await createBankAccount(workspace!.id, memberId, {
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
      await deleteBankAccount(workspace!.id, deleteAccountTarget.memberId, deleteAccountTarget.acc.id!);
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

      {/* Separa conta de login (User) de FamilyMember — evita confusão pós-registro */}
      <Card className="mb-4 border-border/80 bg-muted/15">
        <CardContent className="p-4">
          <p className="text-sm font-medium text-foreground">
            Conta de acesso e pessoas do relatório são coisas diferentes
          </p>
          <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
            O nome e o email do cadastro ficam na sua{" "}
            <span className="font-medium text-foreground/90">conta de login</span> e aparecem na aba{" "}
            <span className="font-medium text-foreground/90">Acessos</span>. Os cartões abaixo são os{" "}
            <span className="font-medium text-foreground/90">membros da família</span> usados no relatório e no pipeline.
            Cadastre cada pessoa com <span className="font-medium text-foreground/90">+ Adicionar membro</span> ou importe um backup na aba Import/Export.
          </p>
        </CardContent>
      </Card>

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
              placeholder="ex: Silva, Campos, etc"
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
        {members.map((m) => {
          const rowKey = m.id ?? m.key;
          const isExpanded = expandedRowKey === rowKey;
          return (
          <Card key={rowKey}>
            <CardContent className="p-0">
              <div className="flex flex-wrap items-center gap-4 px-5 py-4">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-sm font-medium text-primary">
                  {m.short_name.charAt(0).toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-medium">{m.full_name}</p>
                  <p className="text-xs text-muted-foreground">
                    {ROLES.find((r) => r.value === m.role)?.label ?? m.role}
                    {m.cpf && ` · CPF: ***${m.cpf.slice(-4)}`}
                    {m.birth_date && ` · Nasc: ${m.birth_date}`}
                  </p>
                </div>
                <div className="flex shrink-0 flex-wrap items-center justify-end gap-2 sm:flex-nowrap">
                  <span className="text-xs text-muted-foreground">{m.accounts.length} conta(s)</span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setExpandedRowKey(isExpanded ? null : rowKey)}
                  >
                    {isExpanded ? "Fechar" : "Editar"}
                  </Button>
                  {m.id ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-muted-foreground hover:text-destructive"
                      onClick={() => setDeleteTarget(m)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  ) : null}
                </div>
              </div>

              {/* Expanded: modelo (sem id) vs membro persistido */}
              {isExpanded && (
                <div className="border-t border-border px-5 py-4 space-y-4">
                  {!m.id ? (
                    <p className="text-sm text-muted-foreground" data-testid="members-fallback-notice">
                      Estes cartões são só um <strong>modelo</strong> enquanto o workspace ainda não tem membros
                      gravados. Para cadastrar pessoas reais, use <strong>+ Adicionar membro</strong> abaixo ou importe
                      um backup na aba <strong>Import/Export</strong>.
                    </p>
                  ) : (
                    <>
                  <InlineField
                    label="Identificador interno"
                    value={m.key}
                    onSave={(v) => handleUpdate(m, "key", v.trim())}
                    placeholder="ex: maria_silva"
                  />

                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <InlineField label="Nome completo (civil atual)" value={m.full_name} onSave={(v) => handleUpdate(m, "full_name", v)} />
                    <InlineField label="Como prefere ser chamado(a)" value={m.short_name} onSave={(v) => handleUpdate(m, "short_name", v)} />
                    <div className="sm:col-span-2">
                      <InlineField
                        label="Nome civil anterior (opcional)"
                        value={m.birth_name ?? ""}
                        onSave={(v) => handleUpdate(m, "birth_name", v)}
                        placeholder="Ex.: nome em contas antigas ou antes de casar"
                      />
                    </div>
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
                  <div className="space-y-3">
                    <div>
                      <h4 className="mb-1 text-xs font-medium text-muted-foreground uppercase tracking-wide">Contas bancárias</h4>
                      <p className="text-xs text-muted-foreground">
                        Indique em qual membro o pipeline deve considerar cada instituição (extratos, investimentos).
                        Use o código do banco como no restante do sistema (ex.: <code className="rounded bg-muted px-1">itau</code>,{" "}
                        <code className="rounded bg-muted px-1">c6bank</code>) — veja a aba Instituições.
                      </p>
                    </div>
                    {m.accounts.length > 0 && (
                      <div className="space-y-1">
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
                    <form onSubmit={(e) => handleAddAccount(m.id!, e)} className="space-y-2">
                      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
                        <div>
                          <Label className="mb-1 block text-xs text-muted-foreground">Código do banco</Label>
                          <Input name="institution_code" placeholder="itau, c6bank…" required className="text-sm" />
                        </div>
                        <div>
                          <Label className="mb-1 block text-xs text-muted-foreground">Tipo de conta</Label>
                          <Input name="account_type" placeholder="extratoconta" required className="text-sm" />
                        </div>
                        <div>
                          <Label className="mb-1 block text-xs text-muted-foreground">Agência</Label>
                          <Input name="agency" placeholder="Opcional" className="text-sm" />
                        </div>
                        <div>
                          <Label className="mb-1 block text-xs text-muted-foreground">Conta</Label>
                          <Input name="account_number" placeholder="Opcional" className="text-sm" />
                        </div>
                      </div>
                      <Button type="submit" size="sm" variant="secondary" className="w-full sm:w-auto">
                        <Plus className="mr-1.5 h-3.5 w-3.5" />
                        Adicionar conta
                      </Button>
                    </form>
                  </div>
                    </>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
          );
        })}
      </div>

      {/* Add Member Form */}
      {showAdd ? (
        <form onSubmit={handleCreate} className="mt-4 rounded-xl border border-primary/30 bg-primary/5 p-5 space-y-4">
          <div>
            <h3 className="font-medium">Novo membro</h3>
            <p className="mt-1 text-xs text-muted-foreground">
              Não é preciso preencher um &quot;código&quot; técnico: o sistema cria um identificador interno a partir do nome.
              Depois de salvar, o cartão abre para você vincular contas bancárias.
            </p>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <Label className="mb-1 block text-xs text-muted-foreground">Nome completo (civil atual)</Label>
              <Input name="full_name" placeholder="Como nos documentos oficiais" required />
            </div>
            <div>
              <Label className="mb-1 block text-xs text-muted-foreground">Como prefere ser chamado(a)</Label>
              <Input name="short_name" placeholder="Ex.: Maria, David" required />
            </div>
            <div className="sm:col-span-2">
              <Label className="mb-1 block text-xs text-muted-foreground">Nome civil anterior (opcional)</Label>
              <Input name="birth_name" placeholder="Se ainda aparece em extratos ou contratos antigos" />
            </div>
            <div>
              <Label className="mb-1 block text-xs text-muted-foreground">CPF</Label>
              <Input name="cpf" placeholder="11 dígitos" />
            </div>
            <div>
              <Label className="mb-1 block text-xs text-muted-foreground">Nascimento</Label>
              <Input name="birth_date" type="date" />
            </div>
            <div>
              <Label className="mb-1 block text-xs text-muted-foreground">Papel</Label>
              <select name="role" required className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring">
                {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
              </select>
            </div>
            <details className="sm:col-span-2 rounded-lg border border-border/60 bg-background/50 p-3 text-xs">
              <summary className="cursor-pointer font-medium text-foreground">Identificador interno (opcional)</summary>
              <p className="mt-2 text-muted-foreground">
                Só altere se estiver importando dados que já usam uma chave fixa (ex.: <code className="rounded bg-muted px-1">david</code>).
                Requisitos: letras minúsculas, números e underscore; único neste workspace.
              </p>
              <Input name="key" className="mt-2 font-mono text-sm" placeholder="ex.: maria_silva" />
            </details>
          </div>
          <div className="flex gap-2">
            <Button type="submit">Salvar e abrir edição</Button>
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
