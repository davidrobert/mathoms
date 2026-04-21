"use client";

import { Braces } from "lucide-react";
import type { DocumentResponse, ExtractJsonResponse } from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface ExtractJsonModalProps {
  data: { doc: DocumentResponse; result: ExtractJsonResponse } | null;
  onClose: () => void;
}

function CandidatesHint({
  result,
  doc,
}: {
  result: ExtractJsonResponse;
  doc: DocumentResponse;
}) {
  if (result.all_candidates.length <= 1) return null;
  return (
    <p className="text-xs text-muted-foreground mt-1">
      {result.all_candidates.length} extratos disponíveis —
      exibindo melhor correspondência para{" "}
      <span className="font-mono">{doc.bank_code ?? "—"}</span>
      {doc.period ? ` · ${doc.period}` : ""}
    </p>
  );
}

export function ExtractJsonModal({ data, onClose }: ExtractJsonModalProps) {
  const open = !!data;
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[90vh] w-[90vw] !max-w-[90vw] sm:!max-w-[90vw] flex flex-col">
        <DialogHeader className="shrink-0">
          <DialogTitle className="flex items-center gap-2 font-mono text-sm">
            <Braces className="h-4 w-4 shrink-0" />
            <span className="truncate">{data?.result.filename}</span>
          </DialogTitle>
          {data && <CandidatesHint result={data.result} doc={data.doc} />}
        </DialogHeader>
        <div className="flex-1 overflow-auto rounded border bg-muted/40 p-3">
          <pre className="text-xs font-mono whitespace-pre-wrap break-all leading-relaxed">
            {data ? JSON.stringify(data.result.data, null, 2) : ""}
          </pre>
        </div>
      </DialogContent>
    </Dialog>
  );
}
