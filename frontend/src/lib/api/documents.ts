import { API_BASE, ApiError, apiFetch, getToken } from "./core";

// ─── Document Types ───

export type DocumentStatus =
  | "uploaded"
  | "unlocking"
  | "classifying"
  | "ready"
  | "needs_password"
  | "processing"
  | "processed"
  | "error";

export type DocumentType =
  | "bank_statement"
  | "credit_card_bill"
  | "investment_report"
  | "irpf"
  // ADR-238 (A17 L1 P3): informe anual avulso polimórfico, distinto de "irpf".
  | "informe_rendimentos_anuais"
  // ADR-239 (A18 L1 P3): comprovante de bem polimórfico (CRLV em L1; V2 imóveis).
  | "comprovante_bem"
  | "e1_members_json"
  | "e1_5_baseline_json"
  | "other";

export interface DocumentResponse {
  id: string;
  workspace_id: string;
  original_name: string;
  stored_path: string | null;
  doc_type: DocumentType | null;
  e0_doc_type?: string | null;
  bank_code: string | null;
  period: string | null;
  status: DocumentStatus;
  classification_meta: Record<string, unknown> | null;
  classification_confidence?: number | null;
  needs_review?: boolean;
  possible_duplicate_of_id?: string | null;
  file_size_bytes: number | null;
  content_type: string | null;
  error_message: string | null;
  uploaded_at: string;
  pipeline_last_run_at?: string | null;
  pipeline_e2_extract_ok?: boolean | null;
  pipeline_extract_notes?: string | null;
}

export interface DocumentListResponse {
  documents: DocumentResponse[];
  total: number;
}

export interface DocumentUploadResponse {
  documents: DocumentResponse[];
  skipped_duplicates: string[];
  total_uploaded: number;
  total_skipped: number;
}

export interface ExtractJsonResponse {
  filename: string;
  data: unknown;
  all_candidates: string[];
}

export interface ReclassifyResponse {
  total: number;
  updated: number;
  skipped: number;
  errors: number;
}

// ─── Documents ───

export async function uploadDocuments(
  workspaceId: string,
  files: File[],
  onProgress?: (loaded: number, total: number) => void
): Promise<DocumentUploadResponse> {
  const token = getToken();
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/workspaces/${workspaceId}/documents/upload`);
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(e.loaded, e.total);
      }
    });

    const safeParse = (text: string): unknown => {
      try {
        return JSON.parse(text);
      } catch {
        return null;
      }
    };

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        const parsed = safeParse(xhr.responseText);
        if (parsed === null) {
          reject(new ApiError(xhr.status, "Resposta inválida do servidor"));
          return;
        }
        resolve(parsed as DocumentUploadResponse);
      } else {
        const parsed = safeParse(xhr.responseText) as { detail?: string } | null;
        const detail =
          parsed?.detail ||
          (xhr.responseText && xhr.responseText.length < 200 ? xhr.responseText : null) ||
          `HTTP ${xhr.status}`;
        reject(new ApiError(xhr.status, detail));
      }
    });

    xhr.addEventListener("error", () => reject(new Error("Erro de conexão")));
    xhr.addEventListener("abort", () => reject(new Error("Upload cancelado")));
    xhr.addEventListener("timeout", () => reject(new Error("Tempo esgotado no upload")));
    xhr.send(formData);
  });
}

export async function listDocuments(
  workspaceId: string,
  statusFilter?: DocumentStatus | DocumentStatus[],
  docTypeFilter?: DocumentType
): Promise<DocumentListResponse> {
  const params = new URLSearchParams();
  if (statusFilter) {
    const s = Array.isArray(statusFilter) ? statusFilter.join(",") : statusFilter;
    params.set("status", s);
  }
  if (docTypeFilter) params.set("doc_type", docTypeFilter);
  const qs = params.toString();
  return apiFetch(`/workspaces/${workspaceId}/documents${qs ? `?${qs}` : ""}`);
}

export async function deleteDocument(workspaceId: string, documentId: string): Promise<void> {
  return apiFetch(`/workspaces/${workspaceId}/documents/${documentId}`, { method: "DELETE" });
}

/** Corrige manualmente a classificação de um documento (tipo, instituição, período).
 *  Envia apenas os campos presentes — backend faz PATCH parcial. */
export async function updateDocumentClassification(
  workspaceId: string,
  documentId: string,
  data: Partial<Pick<DocumentResponse, "doc_type" | "bank_code" | "period">>,
): Promise<DocumentResponse> {
  return apiFetch(`/workspaces/${workspaceId}/documents/${documentId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function retryUnlock(workspaceId: string): Promise<DocumentResponse[]> {
  return apiFetch(`/workspaces/${workspaceId}/documents/retry-unlock`, { method: "POST" });
}

/**
 * Faz fetch autenticado do arquivo original de um documento e retorna um Blob.
 * PDFs devem ser abertos em nova aba (browser renderiza inline);
 * outros formatos devem ser baixados via <a download>.
 */
export async function fetchDocumentFile(
  workspaceId: string,
  documentId: string,
): Promise<{ blob: Blob; filename: string; contentType: string }> {
  const token = typeof window !== "undefined" ? localStorage.getItem("fin_token") : null;
  const res = await fetch(`${API_BASE}/workspaces/${workspaceId}/documents/${documentId}/file`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new ApiError(res.status, text || res.statusText);
  }
  const cd = res.headers.get("content-disposition") ?? "";
  const nameMatch = cd.match(/filename="?([^";\n]+)"?/);
  const filename = nameMatch ? nameMatch[1] : "documento";
  const blob = await res.blob();
  return { blob, filename, contentType: res.headers.get("content-type") ?? "" };
}

export async function fetchDocumentExtractJson(
  workspaceId: string,
  documentId: string,
): Promise<ExtractJsonResponse> {
  return apiFetch(`/workspaces/${workspaceId}/documents/${documentId}/extract-json`);
}

/** Re-executa o classificador de conteúdo em todos os documentos do workspace.
 *  Documentos com override manual são ignorados por padrão. */
export async function reclassifyDocuments(
  workspaceId: string,
  skipManualOverrides = true,
): Promise<ReclassifyResponse> {
  const qs = skipManualOverrides ? "" : "?skip_manual_overrides=false";
  return apiFetch(`/workspaces/${workspaceId}/documents/reclassify${qs}`, { method: "POST" });
}
