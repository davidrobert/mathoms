"use client";

import * as React from "react";
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";

export interface ColumnDef<T> {
  id: string;
  header: string;
  cell: (row: T) => React.ReactNode;
  sortable?: boolean;
  className?: string;
}

type SortDir = "asc" | "desc" | null;

interface DataTableProps<T> {
  columns: ColumnDef<T>[];
  data: T[];
  loading?: boolean;
  emptyMessage?: string;
  onRowClick?: (row: T) => void;
  selectedRows?: Set<number>;
  onSelectRows?: (selected: Set<number>) => void;
  className?: string;
}

export function DataTable<T>({
  columns,
  data,
  loading = false,
  emptyMessage = "Nenhum registro encontrado.",
  onRowClick,
  selectedRows,
  onSelectRows,
  className,
}: DataTableProps<T>) {
  const [sortCol, setSortCol] = React.useState<string | null>(null);
  const [sortDir, setSortDir] = React.useState<SortDir>(null);

  const handleSort = (colId: string) => {
    if (sortCol !== colId) {
      setSortCol(colId);
      setSortDir("asc");
    } else if (sortDir === "asc") {
      setSortDir("desc");
    } else {
      setSortCol(null);
      setSortDir(null);
    }
  };

  const sorted = React.useMemo(() => {
    if (!sortCol || !sortDir) return data;
    const col = columns.find((c) => c.id === sortCol);
    if (!col) return data;
    return [...data].sort((a, b) => {
      const va = col.cell(a);
      const vb = col.cell(b);
      const sa = typeof va === "string" ? va : String(va ?? "");
      const sb = typeof vb === "string" ? vb : String(vb ?? "");
      const cmp = sa.localeCompare(sb, "pt-BR", { numeric: true });
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [data, sortCol, sortDir, columns]);

  const hasSelection = selectedRows !== undefined && onSelectRows !== undefined;

  const allSelected =
    hasSelection && data.length > 0 && selectedRows!.size === data.length;

  const toggleAll = () => {
    if (!onSelectRows) return;
    if (allSelected) {
      onSelectRows(new Set());
    } else {
      onSelectRows(new Set(data.map((_, i) => i)));
    }
  };

  const toggleRow = (idx: number) => {
    if (!onSelectRows || !selectedRows) return;
    const next = new Set(selectedRows);
    if (next.has(idx)) next.delete(idx);
    else next.add(idx);
    onSelectRows(next);
  };

  const SortIcon = ({ colId }: { colId: string }) => {
    if (sortCol !== colId) return <ArrowUpDown className="ml-1 inline h-3.5 w-3.5 text-muted-foreground/60" />;
    if (sortDir === "asc") return <ArrowUp className="ml-1 inline h-3.5 w-3.5" />;
    return <ArrowDown className="ml-1 inline h-3.5 w-3.5" />;
  };

  const SKELETON_ROWS = 5;

  return (
    <div className={cn("rounded-lg border", className)}>
      <Table>
        <TableHeader className="sticky top-0 z-10 bg-muted/50">
          <TableRow>
            {hasSelection && (
              <TableHead className="w-10">
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={toggleAll}
                  className="accent-primary"
                />
              </TableHead>
            )}
            {columns.map((col) => (
              <TableHead
                key={col.id}
                className={cn(
                  col.sortable && "cursor-pointer select-none",
                  col.className
                )}
                onClick={col.sortable ? () => handleSort(col.id) : undefined}
              >
                {col.header}
                {col.sortable && <SortIcon colId={col.id} />}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading
            ? Array.from({ length: SKELETON_ROWS }).map((_, i) => (
                <TableRow key={i}>
                  {hasSelection && (
                    <TableCell>
                      <Skeleton className="h-4 w-4" />
                    </TableCell>
                  )}
                  {columns.map((col) => (
                    <TableCell key={col.id}>
                      <Skeleton className="h-4 w-24" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            : sorted.length === 0
              ? (
                  <TableRow>
                    <TableCell
                      colSpan={columns.length + (hasSelection ? 1 : 0)}
                      className="h-24 text-center text-muted-foreground"
                    >
                      {emptyMessage}
                    </TableCell>
                  </TableRow>
                )
              : sorted.map((row, idx) => (
                  <TableRow
                    key={idx}
                    className={cn(
                      onRowClick && "cursor-pointer",
                      selectedRows?.has(idx) && "bg-muted"
                    )}
                    onClick={() => onRowClick?.(row)}
                  >
                    {hasSelection && (
                      <TableCell>
                        <input
                          type="checkbox"
                          checked={selectedRows!.has(idx)}
                          onChange={(e) => {
                            e.stopPropagation();
                            toggleRow(idx);
                          }}
                          onClick={(e) => e.stopPropagation()}
                          className="accent-primary"
                        />
                      </TableCell>
                    )}
                    {columns.map((col) => (
                      <TableCell key={col.id} className={col.className}>
                        {col.cell(row)}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
        </TableBody>
      </Table>
    </div>
  );
}
