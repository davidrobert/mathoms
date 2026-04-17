"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  listCategories,
  createCategory,
  updateCategory,
  deleteCategory,
  reclassifyExpenses,
  type CategoryConfig,
  ApiError,
} from "@/lib/api";
import Link from "next/link";
import { Spinner } from "@/components/Spinner";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Trash2, Plus } from "lucide-react";
import { useWorkspace } from "@/lib/WorkspaceProvider";
import type { UserWorkspace } from "@/lib/api";

export default function CategoriesTab() {
  const { workspace } = useWorkspace();
  const [categories, setCategories] = useState<CategoryConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [filter, setFilter] = useState<"all" | "expense" | "income">("all");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<CategoryConfig | null>(null);
  const [reclassifying, setReclassifying] = useState(false);
  const [reclassifyStatus, setReclassifyStatus] = useState<"idle" | "success" | "conflict" | "error">("idle");

  const reload = useCallback(async () => {
    if (!workspace) return;
    try {
      const data = await listCategories(workspace.id);
      setCategories(data.categories);
    } catch {
      setError("Erro ao carregar categorias");
    } finally {
      setLoading(false);
    }
  }, [workspace]);

  useEffect(() => { reload(); }, [reload]);

  if (!workspace) return null;
  return <CategoriesTabContent workspace={workspace} />;
}

function CategoriesTabContent({ workspace }: { workspace: UserWorkspace }) {

  const filtered = categories.filter(
    (c) => filter === "all" || c.category_type === filter
  );
  const expenses = categories.filter((c) => c.category_type === "expense");
  const incomes = categories.filter((c) => c.category_type === "income");

  async function handleCreate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(""); setSuccess("");
    const fd = new FormData(e.currentTarget);
    const kwStr = fd.get("keywords") as string;
    try {
      await createCategory(workspace.id, {
        code: fd.get("code") as string,
        name: fd.get("name") as string,
        category_type: fd.get("category_type") as "expense" | "income",
        monthly_cap: fd.get("monthly_cap") ? Number(fd.get("monthly_cap")) : undefined,
        order: categories.length,
        keywords: kwStr ? kwStr.split(",").map((k) => k.trim()).filter(Boolean) : [],
      });
      setSuccess("Categoria adicionada!");
      setShowAdd(false);
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao adicionar");
    }
  }

  async function handleDelete() {
    if (!deleteTarget?.id) return;
    try {
      await deleteCategory(workspace.id, deleteTarget.id);
      await reload();
    } catch { setError("Erro ao remover"); }
    setDeleteTarget(null);
  }

  async function handleSaveKeywords(cat: CategoryConfig, newKeywords: string[]) {
    if (!cat.id) {
      setError("Esta categoria ainda não foi salva no banco. Remova e recrie para editar keywords.");
      return;
    }
    try {
      await updateCategory(workspace.id, cat.id, { keywords: newKeywords });
      setEditingId(null);
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao atualizar keywords");
    }
  }

  async function handleUpdateCap(cat: CategoryConfig, val: string) {
    if (!cat.id) return;
    try {
      await updateCategory(workspace.id, cat.id, { monthly_cap: val ? Number(val) : null });
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao atualizar teto");
    }
  }

  async function handleReclassify() {
    setReclassifying(true);
    setReclassifyStatus("idle");
    try {
      await reclassifyExpenses(workspace.id);
      setReclassifyStatus("success");
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setReclassifyStatus("conflict");
      } else {
        setReclassifyStatus("error");
      }
    } finally {
      setReclassifying(false);
    }
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

      {/* Stats + Filter */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex gap-2 text-xs">
          <StatusBadge variant="error">{expenses.length} despesas</StatusBadge>
          <StatusBadge variant="success">{incomes.length} receitas</StatusBadge>
          <StatusBadge variant="neutral">
            {categories.reduce((s, c) => s + c.keywords.length, 0)} keywords total
          </StatusBadge>
        </div>
        <div className="flex gap-1 rounded-lg border border-border p-0.5 text-xs">
          {(["all", "expense", "income"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`rounded-md px-2.5 py-1 transition ${
                filter === f ? "bg-card shadow-sm font-medium" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {f === "all" ? "Todas" : f === "expense" ? "Despesas" : "Receitas"}
            </button>
          ))}
        </div>
      </div>

      {/* Category List */}
      <div className="space-y-2">
        {filtered.map((cat) => (
          <CategoryCard
            key={cat.id ?? cat.code}
            cat={cat}
            isEditing={editingId === cat.id}
            onToggleEdit={() => setEditingId(editingId === cat.id ? null : cat.id ?? null)}
            onDelete={() => setDeleteTarget(cat)}
            onSaveKeywords={(kws) => handleSaveKeywords(cat, kws)}
            onUpdateCap={(val) => handleUpdateCap(cat, val)}
          />
        ))}
      </div>

      {/* Add */}
      {showAdd ? (
        <form onSubmit={handleCreate} className="mt-4 rounded-xl border border-primary/30 bg-primary/5 p-5 space-y-3">
          <h3 className="font-medium">Nova Categoria</h3>
          <div className="grid grid-cols-2 gap-3">
            <Input name="code" placeholder="Código (ex: moradia)" required />
            <Input name="name" placeholder="Nome (ex: Moradia)" required />
            <select name="category_type" required className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring">
              <option value="expense">Despesa</option>
              <option value="income">Receita</option>
            </select>
            <Input name="monthly_cap" type="number" step="0.01" placeholder="Teto mensal (opcional)" />
          </div>
          <Textarea name="keywords" placeholder="Keywords separadas por vírgula" rows={2} />
          <div className="flex gap-2">
            <Button type="submit">Salvar</Button>
            <Button type="button" variant="outline" onClick={() => setShowAdd(false)}>Cancelar</Button>
          </div>
        </form>
      ) : (
        <Button variant="outline" className="mt-4 w-full border-dashed" onClick={() => setShowAdd(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Adicionar categoria
        </Button>
      )}

      {/* Reclassify banner */}
      <div className="mt-6 rounded-xl border border-border bg-card p-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium">Aplicar alterações nas transações</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Mudanças em keywords só têm efeito após reclassificar. As etapas E4→E7 serão reprocessadas.
            </p>
            {reclassifyStatus === "success" && (
              <p className="text-xs text-gain mt-1">
                Reclassificação iniciada.{" "}
                <Link href="/pipeline" className="underline">Acompanhe o progresso.</Link>
              </p>
            )}
            {reclassifyStatus === "conflict" && (
              <p className="text-xs text-alert mt-1">
                Já existe uma execução em andamento.{" "}
                <Link href="/pipeline" className="underline">Ver pipeline.</Link>
              </p>
            )}
            {reclassifyStatus === "error" && (
              <p className="text-xs text-loss mt-1">Erro ao iniciar reclassificação. Tente novamente.</p>
            )}
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={handleReclassify}
            disabled={reclassifying}
            className="shrink-0"
          >
            {reclassifying ? <Spinner size="sm" className="mr-2" /> : null}
            Reclassificar Despesas
          </Button>
        </div>
      </div>

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title={`Remover "${deleteTarget?.name}" e suas ${deleteTarget?.keywords.length ?? 0} keywords?`}
        confirmLabel="Remover"
        variant="destructive"
        onConfirm={handleDelete}
      />
    </div>
  );
}

function CategoryCard({ cat, isEditing, onToggleEdit, onDelete, onSaveKeywords, onUpdateCap }: {
  cat: CategoryConfig;
  isEditing: boolean;
  onToggleEdit: () => void;
  onDelete: () => void;
  onSaveKeywords: (kws: string[]) => void;
  onUpdateCap: (val: string) => void;
}) {
  const [kwText, setKwText] = useState(cat.keywords.join(", "));
  const isExpense = cat.category_type === "expense";

  return (
    <Card>
      <CardContent className="p-0">
        <div className="flex items-center gap-3 px-4 py-3">
          <span className={`inline-flex h-2 w-2 rounded-full ${isExpense ? "bg-loss" : "bg-gain"}`} />
          <div className="flex-1">
            <span className="text-sm font-medium">{cat.name}</span>
            <span className="ml-2 text-xs text-muted-foreground">({cat.code})</span>
            {cat.monthly_cap != null && (
              <span className="ml-2 text-xs text-alert">Teto: R$ {cat.monthly_cap.toLocaleString("pt-BR")}</span>
            )}
          </div>
          <span className="text-xs text-muted-foreground">{cat.keywords.length} keywords</span>
          <Button variant="outline" size="sm" onClick={onToggleEdit}>
            {isEditing ? "Fechar" : "Editar"}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="text-muted-foreground hover:text-destructive"
            onClick={onDelete}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>

        {isEditing && (
          <div className="border-t border-border px-4 py-3 space-y-3">
            <div className="flex gap-3">
              <div className="flex-1">
                <Label className="mb-1 text-xs text-muted-foreground">Teto mensal (R$)</Label>
                <Input
                  type="number"
                  step="0.01"
                  defaultValue={cat.monthly_cap ?? ""}
                  placeholder="Sem teto"
                  onBlur={(e) => onUpdateCap(e.target.value)}
                />
              </div>
            </div>
            <div>
              <Label className="mb-1 text-xs text-muted-foreground">Keywords (separadas por vírgula)</Label>
              <Textarea
                value={kwText}
                onChange={(e) => setKwText(e.target.value)}
                rows={3}
                className="font-mono text-xs"
              />
              <Button
                size="sm"
                className="mt-2"
                onClick={() => onSaveKeywords(kwText.split(",").map((k) => k.trim()).filter(Boolean))}
              >
                Salvar keywords
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
