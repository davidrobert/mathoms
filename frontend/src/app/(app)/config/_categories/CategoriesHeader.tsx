"use client";

/**
 * CategoriesHeader — stats + filtros (W4).
 *
 * Contagens (despesas/receitas/personalizadas) + filtro por tipo +
 * switch "Apenas personalizadas". Extraído do CategoriesTab.tsx em 2026-05-10.
 */

import { StatusBadge } from "@/components/StatusBadge";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/cn";

export type CategoryFilter = "all" | "expense" | "income";

interface CategoriesHeaderProps {
  expensesCount: number;
  incomesCount: number;
  customizedCount: number;
  filter: CategoryFilter;
  onFilterChange: (next: CategoryFilter) => void;
  showOnlyCustomized: boolean;
  onShowOnlyCustomizedChange: (next: boolean) => void;
}

export function CategoriesHeader({
  expensesCount,
  incomesCount,
  customizedCount,
  filter,
  onFilterChange,
  showOnlyCustomized,
  onShowOnlyCustomizedChange,
}: CategoriesHeaderProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2">
      <div className="flex flex-wrap gap-2 text-xs">
        <StatusBadge variant="error">{expensesCount} despesas</StatusBadge>
        <StatusBadge variant="success">{incomesCount} receitas</StatusBadge>
        <StatusBadge variant="neutral">{customizedCount} personalizadas</StatusBadge>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <label className="flex items-center gap-2 text-xs text-muted-foreground">
          <Switch
            size="sm"
            checked={showOnlyCustomized}
            onCheckedChange={onShowOnlyCustomizedChange}
            aria-label="Apenas personalizadas"
          />
          Apenas personalizadas
        </label>
        <div className="flex gap-1 rounded-lg border border-border p-0.5 text-xs">
          {(["all", "expense", "income"] as const).map((f) => (
            <button
              key={f}
              onClick={() => onFilterChange(f)}
              className={cn(
                "rounded-md px-2.5 py-1 transition",
                filter === f
                  ? "bg-card font-medium shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {f === "all" ? "Todas" : f === "expense" ? "Despesas" : "Receitas"}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
