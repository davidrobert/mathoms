import type { DocumentResponse } from "@/lib/api";
import { docTypeLabel, institutionLabel } from "@/lib/format";
import { mimeLabel } from "./fileFormat";
import type { SortDir, SortKey } from "./SortableHead";

function extractSortValue(doc: DocumentResponse, key: SortKey): string {
  switch (key) {
    case "original_name":
      return doc.original_name ?? "";
    case "doc_type":
      return docTypeLabel(doc.doc_type);
    case "content_type":
      return mimeLabel(doc.content_type);
    case "bank_code":
      return institutionLabel(doc.bank_code);
    case "period":
      return doc.period ?? "";
    case "status":
      return doc.status ?? "";
    case "uploaded_at":
      return doc.uploaded_at ?? "";
  }
}

export function sortDocs(
  docs: DocumentResponse[],
  sortKey: SortKey,
  sortDir: SortDir,
): DocumentResponse[] {
  return [...docs].sort((a, b) => {
    const av = extractSortValue(a, sortKey);
    const bv = extractSortValue(b, sortKey);
    const cmp = av.localeCompare(bv, "pt-BR", { sensitivity: "base", numeric: true });
    return sortDir === "asc" ? cmp : -cmp;
  });
}
