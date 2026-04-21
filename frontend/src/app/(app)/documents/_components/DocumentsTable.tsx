"use client";

import type { DocumentResponse } from "@/lib/api";
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { TooltipProvider } from "@/components/ui/tooltip";
import { DocumentRow } from "./DocumentRow";
import { SortableHead, type SortDir, type SortKey } from "./SortableHead";

interface DocumentsTableProps {
  docs: DocumentResponse[];
  sortKey: SortKey;
  sortDir: SortDir;
  onSort: (key: SortKey) => void;
  viewingId: string | null;
  loadingExtractId: string | null;
  onView: (d: DocumentResponse) => void;
  onViewExtract: (d: DocumentResponse) => void;
  onEdit: (d: DocumentResponse) => void;
  onRequestDelete: (d: DocumentResponse) => void;
}

export function DocumentsTable({
  docs,
  sortKey,
  sortDir,
  onSort,
  viewingId,
  loadingExtractId,
  onView,
  onViewExtract,
  onEdit,
  onRequestDelete,
}: DocumentsTableProps) {
  const headProps = { sortKey, sortDir, onSort };
  return (
    <div className="rounded-xl border border-border bg-card">
      <TooltipProvider delay={400}>
        <Table>
          <TableHeader>
            <TableRow>
              <SortableHead label="Arquivo" col="original_name" {...headProps} />
              <SortableHead label="Tipo" col="doc_type" {...headProps} />
              <SortableHead label="Formato" col="content_type" {...headProps} />
              <SortableHead label="Instituição" col="bank_code" {...headProps} />
              <SortableHead label="Período" col="period" {...headProps} />
              <SortableHead label="Status" col="status" {...headProps} />
              <TableHead className="w-10"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {docs.map((doc) => (
              <DocumentRow
                key={doc.id}
                doc={doc}
                viewingId={viewingId}
                loadingExtractId={loadingExtractId}
                onView={onView}
                onViewExtract={onViewExtract}
                onEdit={onEdit}
                onRequestDelete={onRequestDelete}
              />
            ))}
          </TableBody>
        </Table>
      </TooltipProvider>
    </div>
  );
}
