"use client";

import {
  AlertCircle,
  AlertTriangle,
  Braces,
  Download,
  Eye,
  Info,
  Pencil,
  Trash2,
} from "lucide-react";
import type { DocumentResponse } from "@/lib/api";
import {
  docEffectiveStatus,
  docTypeLabel,
  formatBytes,
  formatDate,
  formatDocPeriod,
  institutionLabel,
  pipelineE2TouchLabel,
  pipelineTouchTooltipExplanation,
} from "@/lib/format";
import { cn } from "@/lib/cn";
import { StatusBadge } from "@/components/StatusBadge";
import { Spinner } from "@/components/Spinner";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { TableCell, TableRow } from "@/components/ui/table";
import { fileIconFor, mimeLabel } from "./fileFormat";
import { isClassificationUncertain } from "./classificationHints";

function FilenameCell({ doc }: { doc: DocumentResponse }) {
  const Icon = fileIconFor(doc.content_type);
  return (
    <TableCell className="max-w-0 min-w-[200px] align-middle">
      <div className="flex items-center gap-2">
        <span
          className="inline-flex shrink-0 text-muted-foreground"
          title={`${formatBytes(doc.file_size_bytes)} · ${doc.original_name}`}
        >
          <Icon className="h-4 w-4" />
        </span>
        <div className="min-w-0 flex-1">
          <Tooltip>
            <TooltipTrigger
              type="button"
              className="block w-full max-w-full cursor-default truncate border-0 bg-transparent p-0 text-left font-medium leading-tight text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {doc.original_name}
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-md break-words">
              {doc.original_name}
            </TooltipContent>
          </Tooltip>
          <div className="mt-0.5 truncate text-xs text-foreground/70">
            {formatDate(doc.uploaded_at)} · {formatBytes(doc.file_size_bytes)}
          </div>
        </div>
      </div>
    </TableCell>
  );
}

function DocTypeCell({ doc, uncertain }: { doc: DocumentResponse; uncertain: boolean }) {
  return (
    <TableCell className="align-middle">
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "min-w-0 flex-1 truncate",
            uncertain ? "text-foreground" : "text-foreground/75",
          )}
        >
          {docTypeLabel(doc.doc_type)}
        </span>
        {uncertain && (
          <Tooltip>
            <TooltipTrigger
              type="button"
              className="shrink-0 rounded p-0.5 text-warning hover:bg-warning/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label="Classificação incerta — edite tipo e instituição com o ícone de lápis"
            >
              <AlertTriangle className="h-4 w-4" aria-hidden />
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">
              Classificação automática incerta. Use o ícone de lápis para ajustar tipo e instituição.
            </TooltipContent>
          </Tooltip>
        )}
      </div>
    </TableCell>
  );
}

function StatusCell({ doc }: { doc: DocumentResponse }) {
  const st = docEffectiveStatus(doc);
  const pipelineLabel = pipelineE2TouchLabel(doc.pipeline_last_run_at, doc.pipeline_e2_extract_ok);
  return (
    <TableCell className="align-middle">
      <div className="flex items-center gap-1">
        {pipelineLabel !== "—" ? (
          <Tooltip>
            <TooltipTrigger
              type="button"
              className="inline-flex cursor-help border-0 bg-transparent p-0 outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <StatusBadge variant={st.variant}>{st.label}</StatusBadge>
            </TooltipTrigger>
            <TooltipContent className="max-w-sm space-y-1.5 text-left">
              <p className="text-xs font-medium">Última análise</p>
              <p className="text-xs">{pipelineLabel}</p>
              <p className="text-xs text-background/80">
                {pipelineTouchTooltipExplanation(doc.pipeline_e2_extract_ok)}
              </p>
            </TooltipContent>
          </Tooltip>
        ) : (
          <StatusBadge variant={st.variant}>{st.label}</StatusBadge>
        )}
        {doc.error_message && (
          <Tooltip>
            <TooltipTrigger className="cursor-help text-muted-foreground">
              <Info className="inline h-3.5 w-3.5" />
            </TooltipTrigger>
            <TooltipContent>{doc.error_message}</TooltipContent>
          </Tooltip>
        )}
        {doc.pipeline_extract_notes && (
          <Tooltip>
            <TooltipTrigger className="cursor-help text-destructive/70">
              <AlertCircle className="inline h-3.5 w-3.5" aria-label="Notas de extração" />
            </TooltipTrigger>
            <TooltipContent className="max-w-xs whitespace-pre-wrap text-left text-xs">
              {doc.pipeline_extract_notes}
            </TooltipContent>
          </Tooltip>
        )}
      </div>
    </TableCell>
  );
}

function isInlineableContentType(ct: string | null | undefined): boolean {
  return !!ct && (ct.includes("pdf") || ct.includes("image/"));
}

function ActionsCell({
  doc,
  viewingId,
  loadingExtractId,
  onView,
  onViewExtract,
  onEdit,
  onRequestDelete,
}: {
  doc: DocumentResponse;
  viewingId: string | null;
  loadingExtractId: string | null;
  onView: (d: DocumentResponse) => void;
  onViewExtract: (d: DocumentResponse) => void;
  onEdit: (d: DocumentResponse) => void;
  onRequestDelete: (d: DocumentResponse) => void;
}) {
  const inlineable = isInlineableContentType(doc.content_type);
  return (
    <TableCell className="align-middle">
      <div className="flex items-center gap-0.5">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onView(doc)}
          disabled={viewingId === doc.id}
          className="text-muted-foreground hover:text-foreground"
          aria-label={`Visualizar ${doc.original_name}`}
          title={inlineable ? "Abrir no navegador" : "Baixar arquivo"}
        >
          {viewingId === doc.id ? (
            <Spinner size="sm" />
          ) : inlineable ? (
            <Eye className="h-4 w-4" />
          ) : (
            <Download className="h-4 w-4" />
          )}
        </Button>
        {doc.pipeline_e2_extract_ok ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onViewExtract(doc)}
            disabled={loadingExtractId === doc.id}
            className="text-muted-foreground hover:text-foreground"
            aria-label={`Ver JSON extraído de ${doc.original_name}`}
            title="Ver JSON extraído (E2)"
          >
            {loadingExtractId === doc.id ? <Spinner size="sm" /> : <Braces className="h-4 w-4" />}
          </Button>
        ) : (
          <span className="inline-flex h-8 w-8" aria-hidden />
        )}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onEdit(doc)}
          className="text-muted-foreground hover:text-foreground"
          aria-label={`Editar classificação de ${doc.original_name}`}
          title="Editar tipo e instituição"
        >
          <Pencil className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onRequestDelete(doc)}
          className="text-muted-foreground hover:text-destructive"
          aria-label={`Remover ${doc.original_name}`}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </TableCell>
  );
}

export function DocumentRow({
  doc,
  viewingId,
  loadingExtractId,
  onView,
  onViewExtract,
  onEdit,
  onRequestDelete,
}: {
  doc: DocumentResponse;
  viewingId: string | null;
  loadingExtractId: string | null;
  onView: (d: DocumentResponse) => void;
  onViewExtract: (d: DocumentResponse) => void;
  onEdit: (d: DocumentResponse) => void;
  onRequestDelete: (d: DocumentResponse) => void;
}) {
  const uncertain = isClassificationUncertain(doc);
  return (
    <TableRow
      className={cn(uncertain && "border-l-2 border-l-warning/60 bg-warning/[0.04]")}
    >
      <FilenameCell doc={doc} />
      <DocTypeCell doc={doc} uncertain={uncertain} />
      <TableCell className="w-[4.5rem] align-middle">
        <span className="inline-block rounded bg-muted px-1 py-0 font-mono text-[10px] leading-none text-foreground/75">
          {mimeLabel(doc.content_type)}
        </span>
      </TableCell>
      <TableCell className="align-middle text-foreground/75">{institutionLabel(doc.bank_code)}</TableCell>
      <TableCell className="align-middle text-foreground/75">{formatDocPeriod(doc.period)}</TableCell>
      <StatusCell doc={doc} />
      <ActionsCell
        doc={doc}
        viewingId={viewingId}
        loadingExtractId={loadingExtractId}
        onView={onView}
        onViewExtract={onViewExtract}
        onEdit={onEdit}
        onRequestDelete={onRequestDelete}
      />
    </TableRow>
  );
}
