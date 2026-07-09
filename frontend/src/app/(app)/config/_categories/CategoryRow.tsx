"use client";

/**
 * CategoryRow — linha de categoria em CategoriesTab (W4).
 *
 * Extraída do CategoriesTab.tsx em 2026-05-10 para manter o arquivo
 * pai sob 500 linhas (gate T2 do audit_code_style).
 */

import { useState } from "react";
import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { CategoryChipDiff } from "@/components/categories/CategoryChipDiff";
import { cn } from "@/lib/cn";
import { formatCurrency } from "@/lib/format";
import type { CategoryConfig } from "@/lib/api";

export interface ResolvedRow {
  cat: CategoryConfig;
  defaultKeywords: readonly string[];
  isCustomized: boolean;
}

interface CategoryRowProps {
  row: ResolvedRow;
  isEditing: boolean;
  isOutdated: boolean;
  onToggleEdit: () => void;
  onToggleActive: (next: boolean) => void;
  onSaveCap: (value: string) => void;
  onSaveLabel: (value: string) => void;
  onSaveKeywords: (kws: string[]) => void;
  onReset: () => void;
}

export function CategoryRow({
  row,
  isEditing,
  isOutdated,
  onToggleEdit,
  onToggleActive,
  onSaveCap,
  onSaveLabel,
  onSaveKeywords,
  onReset,
}: CategoryRowProps) {
  const { cat, defaultKeywords, isCustomized } = row;
  const isExpense = cat.category_type === "expense";
  const [labelDraft, setLabelDraft] = useState(cat.name);
  // Endpoint `/resolved` já filtra disabled off; switch é affordance de toggle.
  const enabled = true;

  return (
    <Card
      data-testid={`category-row-${cat.code}`}
      className={cn(!enabled && "opacity-50")}
    >
      <CardContent className="p-0">
        <div className="flex flex-wrap items-center gap-3 px-4 py-3">
          <span
            className={cn(
              "inline-flex h-2 w-2 rounded-full",
              isExpense ? "bg-loss" : "bg-gain",
            )}
            aria-hidden
          />
          <div className="flex flex-1 items-center gap-2">
            <span className="text-sm font-medium">{cat.name}</span>
            <span className="text-xs text-muted-foreground">({cat.code})</span>
            {isCustomized && (
              <Badge
                variant="outline"
                className="border-[var(--brand-primary)] bg-[var(--surface-muted)] text-[var(--brand-primary)]"
                data-testid="badge-personalizada"
              >
                Personalizada
              </Badge>
            )}
            {isOutdated && (
              <Tooltip>
                <TooltipTrigger
                  className="inline-flex"
                  data-testid="alert-outdated-template"
                  aria-label="Template global atualizado"
                  render={(props) => (
                    <span {...props}>
                      <AlertCircle
                        className="h-4 w-4 text-[var(--semantic-warning)]"
                        aria-hidden
                      />
                    </span>
                  )}
                />
                <TooltipContent>
                  Há uma versão mais recente do template global de categorias
                  disponível.
                </TooltipContent>
              </Tooltip>
            )}
            {cat.monthly_cap != null && (
              <span className="text-xs text-alert">
                Teto: {formatCurrency(cat.monthly_cap, "BRL", { minimumFractionDigits: 0, maximumFractionDigits: 3 })}
              </span>
            )}
          </div>
          <span className="text-xs text-muted-foreground">
            {cat.keywords.length} keywords
          </span>
          <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Switch
              size="sm"
              checked={enabled}
              onCheckedChange={onToggleActive}
              aria-label="Usar nesta família"
            />
            <span className="hidden sm:inline">Usar nesta família</span>
          </label>
          <Button variant="outline" size="sm" onClick={onToggleEdit}>
            {isEditing ? "Fechar" : "Editar"}
          </Button>
          {isCustomized && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onReset}
              className="text-muted-foreground"
            >
              Restaurar padrão
            </Button>
          )}
        </div>

        {isEditing && (
          <div className="space-y-3 border-t border-border px-4 py-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <Label className="mb-1 text-xs text-muted-foreground">Nome</Label>
                <Input
                  value={labelDraft}
                  onChange={(e) => setLabelDraft(e.target.value)}
                  onBlur={(e) => onSaveLabel(e.target.value)}
                  placeholder={cat.name}
                />
              </div>
              <div>
                <Label className="mb-1 text-xs text-muted-foreground">
                  Teto mensal (R$)
                </Label>
                <Input
                  type="number"
                  step="0.01"
                  defaultValue={cat.monthly_cap ?? ""}
                  placeholder="Sem teto"
                  onBlur={(e) => onSaveCap(e.target.value)}
                />
              </div>
            </div>
            <div>
              <Label className="mb-1.5 block text-xs text-muted-foreground">
                Keywords
              </Label>
              <CategoryChipDiff
                current={cat.keywords}
                defaultKeywords={defaultKeywords}
                onChange={onSaveKeywords}
              />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
