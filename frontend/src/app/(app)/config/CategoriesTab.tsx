"use client";

/**
 * CategoriesTab — A11.cat-overrides-ux W4 (PLAN-category-overrides-ux).
 *
 * Read-path: `/config/category-overrides/resolved` (template global v1 +
 * overrides do workspace, A7.3 · ADR-137). Antes era `/config/categories`
 * (legacy) — workspace novo abria lista vazia. Esta refatoração fecha a
 * feature V1 (24 categorias default-only) com persistência via tabela
 * `workspace_category_overrides`.
 *
 * Tabs/subnav é renderizada a partir de array configurável (1 entrada em
 * V1) — hook estrutural para sub-tab "Regras promovidas" do A12 learning
 * loop (gate dogfood). Adicionar 2ª tab daqui 60d é diff de array.
 */

import { ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import {
  disableCategoryOverride,
  listCategoriesResolved,
  reclassifyExpenses,
  resetCategoryOverride,
  upsertCategoryOverride,
  type CategoryConfig,
  type CategoryListResponseV2,
  ApiError,
} from "@/lib/api";
import { toast } from "sonner";
import { Spinner } from "@/components/Spinner";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useWorkspace } from "@/lib/WorkspaceProvider";
import { useCurrentUser } from "@/lib/useCurrentUser";
import type { UserWorkspace } from "@/lib/api";
import { CategoryRow, type ResolvedRow } from "./_categories/CategoryRow";
import {
  CategoriesHeader,
  type CategoryFilter,
} from "./_categories/CategoriesHeader";
import {
  ReclassifyBanner,
  type ReclassifyStatus,
} from "./_categories/ReclassifyBanner";

// ─── Tipos auxiliares ───────────────────────────────────────────────────

/** Forma de cada entrada do array de tabs.
 *
 * Hook estrutural para A12.cat-learning-loop (V2.A · "Regras promovidas").
 * Adicionar nova entrada NÃO exige refactor de layout — é diff de array.
 */
interface CategoryTabSpec {
  id: string;
  label: string;
  content: ReactNode;
}

// ─── Componente raiz ─────────────────────────────────────────────────────

export default function CategoriesTab() {
  const { workspace } = useWorkspace();
  if (!workspace) return null;
  return <CategoriesTabContent workspace={workspace} />;
}

function CategoriesTabContent({ workspace }: { workspace: UserWorkspace }) {
  const { user } = useCurrentUser();
  const isDeveloper = user?.is_developer ?? false;

  const [data, setData] = useState<CategoryListResponseV2 | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<CategoryFilter>("all");
  const [showOnlyCustomized, setShowOnlyCustomized] = useState(false);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [resetTarget, setResetTarget] = useState<CategoryConfig | null>(null);
  const [reclassifying, setReclassifying] = useState(false);
  const [reclassifyStatus, setReclassifyStatus] =
    useState<ReclassifyStatus>("idle");

  const reload = useCallback(async () => {
    try {
      const fresh = await listCategoriesResolved(workspace.id);
      setData(fresh);
    } catch {
      setError("Erro ao carregar categorias");
    } finally {
      setLoading(false);
    }
  }, [workspace.id]);

  useEffect(() => {
    reload();
  }, [reload]);

  // O endpoint `/resolved` mergeia template + override antes de devolver,
  // não temos `default_keywords` separado no DTO atual — derivamos pelo
  // campo `keywords`. Em V2 do DTO o backend deve carregar
  // `default_keywords` por categoria explicitamente.
  const rows: ResolvedRow[] = useMemo(() => {
    if (!data) return [];
    return data.categories.map((cat) => ({
      cat,
      defaultKeywords: cat.keywords,
      isCustomized: cat.id != null,
    }));
  }, [data]);

  const filtered = rows.filter((r) => {
    const typeOk = filter === "all" || r.cat.category_type === filter;
    const customOk = !showOnlyCustomized || r.isCustomized;
    return typeOk && customOk;
  });
  const expenses = rows.filter((r) => r.cat.category_type === "expense");
  const incomes = rows.filter((r) => r.cat.category_type === "income");
  const customizedCount = rows.filter((r) => r.isCustomized).length;
  const isOutdatedTemplate =
    data != null && data.template_version_used < data.latest_template_version;

  async function handleSaveCap(cat: CategoryConfig, value: string) {
    try {
      const cap = value === "" ? null : Number(value);
      await upsertCategoryOverride(workspace.id, cat.code, { monthly_cap: cap }, "cap");
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao atualizar teto");
    }
  }

  async function handleSaveLabel(cat: CategoryConfig, value: string) {
    if (value === cat.name || value.trim() === "") return;
    try {
      await upsertCategoryOverride(workspace.id, cat.code, { name: value }, "label");
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao atualizar nome");
    }
  }

  async function handleSaveKeywords(cat: CategoryConfig, kws: string[]) {
    try {
      await upsertCategoryOverride(workspace.id, cat.code, { keywords: kws }, "keywords");
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao atualizar keywords");
    }
  }

  async function handleToggleActive(cat: CategoryConfig, nextActive: boolean) {
    try {
      if (nextActive) {
        await resetCategoryOverride(workspace.id, cat.code);
      } else {
        await disableCategoryOverride(workspace.id, cat.code);
      }
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao alternar categoria");
    }
  }

  async function handleResetConfirmed(cat: CategoryConfig) {
    try {
      await resetCategoryOverride(workspace.id, cat.code);
      await reload();
      // V1 oferece undo só como copy ("Padrão restaurado") sem ação reversa.
      // V2 do learning loop pode capturar pre-state e restaurar.
      toast.success("Padrão restaurado", {
        description: `${cat.name} voltou às keywords default.`,
        duration: 8000,
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao restaurar padrão");
    }
    setResetTarget(null);
  }

  function requestReset(cat: CategoryConfig) {
    if (!hasCustomKeywords(cat)) {
      void handleResetConfirmed(cat);
      return;
    }
    setResetTarget(cat);
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

  const categoriesContent = (
    <div className="space-y-4">
      {error && (
        <div className="rounded-lg bg-loss/10 p-3 text-sm text-loss">
          {error}{" "}
          <button onClick={() => setError("")} className="ml-2 underline">
            fechar
          </button>
        </div>
      )}

      <CategoriesHeader
        expensesCount={expenses.length}
        incomesCount={incomes.length}
        customizedCount={customizedCount}
        filter={filter}
        onFilterChange={setFilter}
        showOnlyCustomized={showOnlyCustomized}
        onShowOnlyCustomizedChange={setShowOnlyCustomized}
      />

      <div className="space-y-2">
        {filtered.length === 0 && (
          <div className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
            {showOnlyCustomized
              ? "Nenhuma categoria foi personalizada ainda. Edite o teto, nome ou keywords para criar uma personalização."
              : "Nenhuma categoria encontrada para este filtro."}
          </div>
        )}
        {filtered.map((row) => (
          <CategoryRow
            key={row.cat.code}
            row={row}
            isEditing={editingKey === row.cat.code}
            isOutdated={isOutdatedTemplate}
            onToggleEdit={() =>
              setEditingKey(editingKey === row.cat.code ? null : row.cat.code)
            }
            onToggleActive={(next) => handleToggleActive(row.cat, next)}
            onSaveCap={(val) => handleSaveCap(row.cat, val)}
            onSaveLabel={(val) => handleSaveLabel(row.cat, val)}
            onSaveKeywords={(kws) => handleSaveKeywords(row.cat, kws)}
            onReset={() => requestReset(row.cat)}
          />
        ))}
      </div>

      {isDeveloper && (
        <ReclassifyBanner
          reclassifying={reclassifying}
          status={reclassifyStatus}
          onReclassify={handleReclassify}
        />
      )}

      <ConfirmDialog
        open={!!resetTarget}
        onOpenChange={(open) => !open && setResetTarget(null)}
        title={`Restaurar "${resetTarget?.name}" ao padrão?`}
        description={
          resetTarget
            ? `Isto descartará suas ${resetTarget.keywords.length} keywords personalizadas e voltará às keywords default do template.`
            : undefined
        }
        confirmLabel="Restaurar padrão"
        variant="destructive"
        onConfirm={() => {
          if (resetTarget) handleResetConfirmed(resetTarget);
        }}
      />
    </div>
  );

  // Hook extensível: array de tabs (V1 = 1 entrada).
  // A12.cat-learning-loop V2.A insere uma 2ª entrada aqui (sub-tab
  // "Regras promovidas") condicional ao gate dogfood.
  const tabs: CategoryTabSpec[] = [
    { id: "categories", label: "Categorias", content: categoriesContent },
  ];

  return (
    <TooltipProvider>
      <div>
        {tabs.length === 1 ? (
          tabs[0].content
        ) : (
          <Tabs defaultValue={tabs[0].id} className="w-full">
            <TabsList>
              {tabs.map((t) => (
                <TabsTrigger key={t.id} value={t.id}>
                  {t.label}
                </TabsTrigger>
              ))}
            </TabsList>
            {tabs.map((t) => (
              <TabsContent key={t.id} value={t.id}>
                {t.content}
              </TabsContent>
            ))}
          </Tabs>
        )}
      </div>
    </TooltipProvider>
  );
}

/** Heurística para decidir se reset destrói trabalho do usuário.
 *
 * Como o DTO atual mergeia template + override, não temos o
 * `default_keywords` separado — usamos `isCustomized` (id != null) como
 * sinal seguro: qualquer categoria com row em
 * `workspace_category_overrides` pode ter keywords custom; modal de
 * confirmação cobre o falso-positivo.
 */
function hasCustomKeywords(cat: CategoryConfig): boolean {
  return cat.id != null;
}
