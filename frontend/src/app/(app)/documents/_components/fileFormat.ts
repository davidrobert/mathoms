/** Helpers para exibir tipo de arquivo na tabela de documentos. */

import { File, FileSpreadsheet, FileText, BarChart3, Wrench } from "lucide-react";

export function fileIconFor(contentType: string | null) {
  if (!contentType) return File;
  if (contentType.includes("pdf")) return FileText;
  if (contentType.includes("csv") || contentType.includes("spreadsheet") || contentType.includes("excel"))
    return FileSpreadsheet;
  if (contentType.includes("image")) return BarChart3;
  if (contentType.includes("json")) return Wrench;
  return File;
}

/** Converts a MIME type string into a short human-readable format label. */
export function mimeLabel(contentType: string | null): string {
  if (!contentType) return "—";
  if (contentType.includes("pdf")) return "PDF";
  if (contentType.includes("csv")) return "CSV";
  if (contentType.includes("openxmlformats") || contentType.includes("spreadsheetml")) return "XLSX";
  if (contentType.includes("ms-excel") || contentType.includes("xls")) return "XLS";
  if (contentType.includes("jpeg") || contentType.includes("jpg")) return "JPG";
  if (contentType.includes("png")) return "PNG";
  if (contentType.includes("json")) return "JSON";
  // Fallback: take the subtype portion (e.g. "application/octet-stream" → "octet-stream")
  const sub = contentType.split("/")[1];
  return sub ? sub.toUpperCase().slice(0, 8) : contentType.slice(0, 8).toUpperCase();
}
