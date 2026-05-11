"use client";

import { Check, Pencil, Sparkles, Undo2, X } from "lucide-react";
import type { TransactionItem } from "@/lib/api";
import { bankLabel, formatCurrency, formatDateShort } from "@/lib/format";
import { cn } from "@/lib/cn";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TableCell, TableRow } from "@/components/ui/table";

interface TransactionRowProps {
  tx: TransactionItem;
  categoryOptions: string[];
  editing: boolean;
  editCategory: string;
  savingOverride: boolean;
  onStartEdit: (tx: TransactionItem) => void;
  onCancelEdit: () => void;
  onEditCategoryChange: (v: string) => void;
  onSaveOverride: (hash: string) => void;
  onRemoveOverride: (hash: string) => void;
}

function CategoryEditor({
  value,
  options,
  saving,
  onChange,
  onSave,
  onCancel,
}: {
  value: string;
  options: string[];
  saving: boolean;
  onChange: (v: string) => void;
  onSave: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="flex items-center gap-1">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-7 rounded-md border border-input bg-transparent px-2 text-xs outline-none focus:border-ring focus:ring-1 focus:ring-ring/50"
      >
        {options.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>
      <Button variant="ghost" size="icon-xs" disabled={saving} onClick={onSave}>
        <Check className="h-3.5 w-3.5 text-gain" />
      </Button>
      <Button variant="ghost" size="icon-xs" onClick={onCancel}>
        <X className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}

function CategoryBadge({
  tx,
  onStartEdit,
  onRemoveOverride,
}: {
  tx: TransactionItem;
  onStartEdit: (tx: TransactionItem) => void;
  onRemoveOverride: (hash: string) => void;
}) {
  const isRuleOrigin = tx.is_overridden && tx.override_source === "rule";
  return (
    <span className="inline-flex items-center gap-1">
      <Badge
        variant="outline"
        className="cursor-pointer hover:bg-accent"
        onClick={() => onStartEdit(tx)}
      >
        {tx.categoria || "—"}
        <Pencil className="ml-0.5 h-2.5 w-2.5 opacity-50" />
      </Badge>
      {isRuleOrigin && (
        // A12 P4 — sinal visual de origem ``rule`` (ADR-186/188).
        <Badge
          variant="secondary"
          aria-label="Categorizada automaticamente por regra"
          title="Categorizada automaticamente pela regra. Editar a categoria desta transação preserva sua escolha (sticky)."
          data-testid="rule-source-badge"
          className="h-4 gap-0.5 px-1 text-[10px]"
        >
          <Sparkles className="h-2.5 w-2.5" />
          Regra
        </Badge>
      )}
      {tx.is_overridden && tx.override_source !== "rule" && (
        <span className="inline-flex items-center gap-0.5">
          <Badge variant="secondary" className="h-4 px-1 text-[10px]">
            editado
          </Badge>
          <button
            onClick={() => onRemoveOverride(tx.transaction_hash)}
            className="text-muted-foreground hover:text-foreground"
            title="Desfazer override"
          >
            <Undo2 className="h-3 w-3" />
          </button>
        </span>
      )}
    </span>
  );
}

export function TransactionRow({
  tx,
  categoryOptions,
  editing,
  editCategory,
  savingOverride,
  onStartEdit,
  onCancelEdit,
  onEditCategoryChange,
  onSaveOverride,
  onRemoveOverride,
}: TransactionRowProps) {
  return (
    <TableRow>
      <TableCell className="font-mono text-xs tabular-nums text-muted-foreground">
        {formatDateShort(tx.data)}
      </TableCell>
      <TableCell className="max-w-[300px] truncate" title={tx.descricao}>
        {tx.descricao}
      </TableCell>
      <TableCell>
        {editing ? (
          <CategoryEditor
            value={editCategory}
            options={categoryOptions}
            saving={savingOverride}
            onChange={onEditCategoryChange}
            onSave={() => onSaveOverride(tx.transaction_hash)}
            onCancel={onCancelEdit}
          />
        ) : (
          <CategoryBadge
            tx={tx}
            onStartEdit={onStartEdit}
            onRemoveOverride={onRemoveOverride}
          />
        )}
      </TableCell>
      <TableCell
        className={cn(
          "text-right font-mono text-sm tabular-nums font-medium",
          tx.valor >= 0 ? "text-gain" : "text-loss",
        )}
      >
        {formatCurrency(tx.valor, tx.moeda === "USD" ? "USD" : "BRL")}
      </TableCell>
      <TableCell className="text-muted-foreground">{bankLabel(tx.banco)}</TableCell>
      <TableCell className="text-muted-foreground">{tx.titular || "—"}</TableCell>
    </TableRow>
  );
}
