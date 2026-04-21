"use client";

import { ChevronDown, ChevronUp, ChevronsUpDown } from "lucide-react";
import { TableHead } from "@/components/ui/table";

export type SortKey =
  | "original_name"
  | "doc_type"
  | "content_type"
  | "bank_code"
  | "period"
  | "status"
  | "uploaded_at";
export type SortDir = "asc" | "desc";

export function SortableHead({
  label,
  col,
  sortKey,
  sortDir,
  onSort,
  className,
}: {
  label: string;
  col: SortKey;
  sortKey: SortKey;
  sortDir: SortDir;
  onSort: (key: SortKey) => void;
  className?: string;
}) {
  const active = sortKey === col;
  const textClass = active ? "text-foreground" : "text-muted-foreground";
  return (
    <TableHead className={className}>
      <button
        onClick={() => onSort(col)}
        className={`inline-flex items-center gap-1 rounded px-1 -mx-1 py-0.5 text-xs font-medium transition-colors hover:text-foreground select-none ${textClass}`}
        title={`Ordenar por ${label}`}
      >
        {label}
        {active ? (
          sortDir === "asc" ? (
            <ChevronUp className="h-3 w-3 shrink-0" />
          ) : (
            <ChevronDown className="h-3 w-3 shrink-0" />
          )
        ) : (
          <ChevronsUpDown className="h-3 w-3 shrink-0 opacity-40" />
        )}
      </button>
    </TableHead>
  );
}
