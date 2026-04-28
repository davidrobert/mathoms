"use client";

import type { TransactionItem } from "@/lib/api";
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { TransactionRow } from "./TransactionRow";

interface TransactionsTableProps {
  transactions: TransactionItem[];
  categoryOptions: string[];
  editingRowId: string | null;
  editCategory: string;
  savingOverride: boolean;
  onStartEdit: (tx: TransactionItem) => void;
  onCancelEdit: () => void;
  onEditCategoryChange: (v: string) => void;
  onSaveOverride: (hash: string) => void;
  onRemoveOverride: (hash: string) => void;
}

export function TransactionsTable(props: TransactionsTableProps) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-card">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Data</TableHead>
            <TableHead className="min-w-[200px]">Descrição</TableHead>
            <TableHead>Categoria</TableHead>
            <TableHead className="text-right font-mono tabular-nums">Valor</TableHead>
            <TableHead>Banco</TableHead>
            <TableHead>Titular</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {props.transactions.map((tx) => (
            <TransactionRow
              key={tx.row_id}
              tx={tx}
              categoryOptions={props.categoryOptions}
              editing={props.editingRowId === tx.row_id}
              editCategory={props.editCategory}
              savingOverride={props.savingOverride}
              onStartEdit={props.onStartEdit}
              onCancelEdit={props.onCancelEdit}
              onEditCategoryChange={props.onEditCategoryChange}
              onSaveOverride={props.onSaveOverride}
              onRemoveOverride={props.onRemoveOverride}
            />
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
