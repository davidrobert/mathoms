"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  listDocuments,
  uploadDocuments,
  deleteDocument,
  retryUnlock,
  reclassifyDocuments,
  fetchDocumentFile,
  fetchDocumentExtractJson,
  type DocumentResponse,
  type ExtractJsonResponse,
  ApiError,
} from "@/lib/api";
import {
  formatBytes,
  formatDate,
  formatDocPeriod,
  docEffectiveStatus,
  docTypeLabel,
  institutionLabel,
  pipelineE2TouchLabel,
  pipelineTouchTooltipExplanation,
  isDocumentClassifiedOk,
} from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { Spinner } from "@/components/Spinner";
import { EmptyState } from "@/components/EmptyState";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { EditDocumentDialog } from "@/components/EditDocumentDialog";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Upload,
  Trash2,
  FileText,
  CreditCard,
  BarChart3,
  FileSpreadsheet,
  File,
  Wrench,
  Info,
  KeyRound,
  Pencil,
  RefreshCw,
  Braces,
  Eye,
  Download,
  ChevronUp,
  ChevronDown,
  ChevronsUpDown,
  AlertTriangle,
  AlertCircle,
} from "lucide-react";
import { useWorkspace } from "@/lib/WorkspaceProvider";
import type { UserWorkspace } from "@/lib/api";
import { cn } from "@/lib/cn";

/** Alinhado a ``_REVIEW_CONFIDENCE_THRESHOLD`` no backend (document_classification). */
const CLASSIFICATION_LOW_CONFIDENCE = 0.7;

function isClassificationUncertain(doc: DocumentResponse): boolean {
  if (!isDocumentClassifiedOk(doc.status)) return false;
  if (doc.needs_review) return true;
  const c = doc.classification_confidence;
  return c != null && c < CLASSIFICATION_LOW_CONFIDENCE;
}

export default function DocumentsPage() {
  const { workspace } = useWorkspace();
  if (!workspace) return null;
  return <DocumentsPageContent workspace={workspace} />;
}

function DocumentsPageContent({ workspace }: { workspace: UserWorkspace }) {
  const [docs, setDocs] = useState<DocumentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);
  const [editTarget, setEditTarget] = useState<DocumentResponse | null>(null);
  const [reclassifying, setReclassifying] = useState(false);
  const [viewingId, setViewingId] = useState<string | null>(null);

  const [sortKey, setSortKey] = useState<SortKey>("uploaded_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [reviewFilter, setReviewFilter] = useState<"all" | "uncertain">("all");
  const [extractModal, setExtractModal] = useState<{ doc: DocumentResponse; result: ExtractJsonResponse } | null>(null);
  const [loadingExtractId, setLoadingExtractId] = useState<string | null>(null);

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  const sortedDocs = [...docs].sort((a, b) => {
    let av: string = "";
    let bv: string = "";
    if (sortKey === "original_name") { av = a.original_name ?? ""; bv = b.original_name ?? ""; }
    else if (sortKey === "doc_type")    { av = docTypeLabel(a.doc_type); bv = docTypeLabel(b.doc_type); }
    else if (sortKey === "content_type") { av = mimeLabel(a.content_type); bv = mimeLabel(b.content_type); }
    else if (sortKey === "bank_code")   { av = institutionLabel(a.bank_code); bv = institutionLabel(b.bank_code); }
    else if (sortKey === "period")      { av = a.period ?? ""; bv = b.period ?? ""; }
    else if (sortKey === "status")      { av = a.status ?? ""; bv = b.status ?? ""; }
    else if (sortKey === "uploaded_at") { av = a.uploaded_at ?? ""; bv = b.uploaded_at ?? ""; }
    const cmp = av.localeCompare(bv, "pt-BR", { sensitivity: "base", numeric: true });
    return sortDir === "asc" ? cmp : -cmp;
  });

  const needsPasswordDocs = docs.filter((d) => d.status === "needs_password");
  const readyDocs = docs.filter((d) => isDocumentClassifiedOk(d.status));
  const uncertainClassificationDocs = docs.filter(isClassificationUncertain);

  const displayedDocs =
    reviewFilter === "uncertain"
      ? sortedDocs.filter(isClassificationUncertain)
      : sortedDocs;

  useEffect(() => {
    if (reviewFilter === "uncertain" && uncertainClassificationDocs.length === 0) {
      setReviewFilter("all");
    }
  }, [reviewFilter, uncertainClassificationDocs.length]);

  const reload = useCallback(async () => {
    try {
      const data = await listDocuments(workspace!.id);
      setDocs(data.documents);
    } catch {
      setError("Erro ao carregar documentos");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  async function handleUpload(files: FileList | File[]) {
    const fileArray = Array.from(files);
    if (fileArray.length === 0) return;

    setError("");
    setSuccessMsg("");
    setUploading(true);
    setUploadProgress(0);

    try {
      const result = await uploadDocuments(workspace!.id, fileArray, (loaded, total) => {
        setUploadProgress(Math.round((loaded / total) * 100));
      });
      const uploaded = result.documents;
      const readyCount = uploaded.filter((d) => isDocumentClassifiedOk(d.status)).length;
      const errorCount = uploaded.filter((d) => d.status === "error").length;
      const needsPw = uploaded.filter((d) => d.status === "needs_password").length;

      let msg = `${uploaded.length} arquivo(s) enviado(s).`;
      if (readyCount > 0) msg += ` ${readyCount} pronto(s).`;
      if (needsPw > 0) msg += ` ${needsPw} precisa(m) de senha.`;
      if (errorCount > 0) msg += ` ${errorCount} com erro.`;
      if (result.total_skipped > 0) {
        msg += ` ${result.total_skipped} duplicado(s) ignorado(s).`;
      }
      setSuccessMsg(msg);
      await reload();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : "Erro ao enviar arquivos. Tente novamente."
      );
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    try {
      await deleteDocument(workspace!.id, deleteTarget.id);
      setDocs((prev) => prev.filter((d) => d.id !== deleteTarget.id));
    } catch {
      setError("Erro ao remover documento");
    } finally {
      setDeleteTarget(null);
    }
  }

  async function handleReclassify() {
    setError("");
    setReclassifying(true);
    try {
      const result = await reclassifyDocuments(workspace!.id);
      setSuccessMsg(
        `Reclassificação concluída: ${result.updated} atualizado(s), ${result.skipped} ignorado(s)${result.errors > 0 ? `, ${result.errors} com erro` : ""}.`
      );
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao reclassificar documentos");
    } finally {
      setReclassifying(false);
    }
  }

  async function handleViewDocument(doc: DocumentResponse) {
    if (viewingId) return; // evita cliques duplos
    setViewingId(doc.id);
    setError("");
    try {
      const { blob, filename, contentType } = await fetchDocumentFile(workspace.id, doc.id);
      const url = URL.createObjectURL(blob);
      const isInlineable =
        contentType.includes("pdf") ||
        contentType.includes("image/"); // JPG, PNG, GIF, WebP, etc.
      if (isInlineable) {
        // PDFs e imagens abrem inline no browser em nova aba
        const tab = window.open(url, "_blank");
        // Revoga a URL temporária depois que o browser carregou o arquivo
        if (tab) {
          setTimeout(() => URL.revokeObjectURL(url), 60_000);
        } else {
          URL.revokeObjectURL(url);
          setError("O popup foi bloqueado. Permita popups para este site e tente novamente.");
        }
      } else {
        // Demais formatos (CSV, XLS, XLSX, JSON…): download via link temporário
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao abrir o documento.");
    } finally {
      setViewingId(null);
    }
  }

  async function handleViewExtract(doc: DocumentResponse) {
    if (loadingExtractId) return;
    setLoadingExtractId(doc.id);
    setError("");
    try {
      const result = await fetchDocumentExtractJson(workspace.id, doc.id);
      setExtractModal({ doc, result });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao carregar extrato JSON.");
    } finally {
      setLoadingExtractId(null);
    }
  }

  async function handleRetryUnlock() {
    setError("");
    try {
      const result = await retryUnlock(workspace!.id);
      const unlocked = result.filter((d) => d.status === "ready").length;
      setSuccessMsg(
        unlocked > 0
          ? `${unlocked} documento(s) desbloqueado(s)!`
          : "Nenhum documento conseguiu ser desbloqueado."
      );
      await reload();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : "Erro ao tentar desbloquear"
      );
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      handleUpload(e.dataTransfer.files);
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <PageHeader
        title="Documentos"
        description="Envie extratos, faturas e documentos financeiros"
        actions={
          readyDocs.length > 0 ? (
            <Button nativeButton={false} render={<Link href="/pipeline" />}>
              Gerar Relatório ({readyDocs.length} doc{readyDocs.length > 1 ? "s" : ""})
            </Button>
          ) : undefined
        }
      />

      {/* Messages */}
      {error && (
        <div className="mb-4 rounded-lg bg-loss/10 p-3 text-sm text-loss">
          {error}
          <button onClick={() => setError("")} className="ml-2 font-medium underline">
            fechar
          </button>
        </div>
      )}
      {successMsg && (
        <div className="mb-4 rounded-lg bg-gain/10 p-3 text-sm text-gain">
          {successMsg}
          <button onClick={() => setSuccessMsg("")} className="ml-2 font-medium underline">
            fechar
          </button>
        </div>
      )}

      {/* Upload Zone */}
      <Card
        className={`mb-6 cursor-pointer border-2 border-dashed p-8 text-center transition ${
          dragOver
            ? "border-primary bg-primary/5"
            : "border-border hover:border-muted-foreground"
        } ${uploading ? "pointer-events-none opacity-60" : ""}`}
        onDragOver={(e: React.DragEvent) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.csv,.xlsx,.xls,.jpg,.jpeg,.png,.json"
          className="hidden"
          aria-label="Selecionar arquivos para upload"
          onChange={(e) => e.target.files && handleUpload(e.target.files)}
        />
        {uploading ? (
          <div>
            <div className="mx-auto mb-3 h-2 w-64 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
            <p className="text-sm text-muted-foreground">Enviando... {uploadProgress}%</p>
          </div>
        ) : (
          <>
            <Upload className="mx-auto mb-3 h-10 w-10 text-muted-foreground" />
            <p className="text-sm font-medium">
              Arraste arquivos aqui ou clique para selecionar
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              PDF, CSV, XLSX, JPG, PNG, JSON — até 20 arquivos, 50MB cada
            </p>
          </>
        )}
      </Card>

      {/* Needs Password Banner */}
      {needsPasswordDocs.length > 0 && (
        <div className="mb-4 flex items-center justify-between rounded-lg bg-alert/10 px-4 py-3">
          <p className="text-sm text-alert">
            <KeyRound className="mr-1.5 inline-block h-4 w-4" />
            <span className="font-medium">{needsPasswordDocs.length}</span> documento(s)
            protegido(s) por senha.{" "}
            <Link href="/vault" className="underline">
              Adicione senhas no vault
            </Link>{" "}
            e tente novamente.
          </p>
          <Button variant="outline" size="sm" onClick={handleRetryUnlock}>
            Tentar desbloquear
          </Button>
        </div>
      )}

      {/* Lista: filtro de revisão + reclassificação em massa */}
      {!loading && docs.length > 0 && (
        <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-h-9 flex-wrap items-center gap-2">
            {uncertainClassificationDocs.length > 0 ? (
              <>
                <span className="text-sm text-foreground/85">
                  <span className="font-medium text-warning">
                    {uncertainClassificationDocs.length}
                  </span>{" "}
                  {uncertainClassificationDocs.length === 1
                    ? "documento precisa de revisão da classificação"
                    : "documentos precisam de revisão da classificação"}
                </span>
                <Button
                  type="button"
                  variant={reviewFilter === "uncertain" ? "secondary" : "outline"}
                  size="sm"
                  onClick={() =>
                    setReviewFilter((f) => (f === "uncertain" ? "all" : "uncertain"))
                  }
                  aria-pressed={reviewFilter === "uncertain"}
                >
                  {reviewFilter === "uncertain" ? "Mostrar todos" : "Mostrar só estes"}
                </Button>
              </>
            ) : (
              <span className="text-sm text-muted-foreground">
                {docs.length} {docs.length === 1 ? "documento" : "documentos"} na lista
              </span>
            )}
          </div>
          <Button
            variant="outline"
            size="sm"
            className="shrink-0 self-start sm:self-auto"
            onClick={handleReclassify}
            disabled={reclassifying}
            title="Re-executa o classificador de conteúdo em todos os documentos (útil após atualizações de regras ou upload com extensão errada)"
          >
            {reclassifying ? (
              <span className="inline-flex items-center gap-2">
                <Spinner size="sm" />
                Reclassificando...
              </span>
            ) : (
              <span className="inline-flex items-center gap-2">
                <RefreshCw className="h-3.5 w-3.5" />
                Reclassificar documentos
              </span>
            )}
          </Button>
        </div>
      )}

      {/* Documents Table */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Spinner size="lg" />
        </div>
      ) : docs.length === 0 ? (
        <EmptyState
          variant="no-documents"
          title="Nenhum documento enviado."
          description="Envie seus extratos bancários, faturas de cartão e declarações de IRPF."
          action={{ label: "Enviar documentos", onClick: () => fileInputRef.current?.click() }}
        />
      ) : (
        <div className="rounded-xl border border-border bg-card">
          <TooltipProvider delay={400}>
            <Table>
              <TableHeader>
                <TableRow>
                  <SortableHead label="Arquivo"     col="original_name" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                  <SortableHead label="Tipo"        col="doc_type"      sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                  <SortableHead label="Formato"     col="content_type"  sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                  <SortableHead label="Instituição" col="bank_code"     sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                  <SortableHead label="Período"     col="period"        sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                  <SortableHead label="Status"      col="status"        sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                  <TableHead className="w-10"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {displayedDocs.map((doc) => {
                  const st = docEffectiveStatus(doc);
                  const uncertain = isClassificationUncertain(doc);
                  const pipelineLabel = pipelineE2TouchLabel(
                    doc.pipeline_last_run_at,
                    doc.pipeline_e2_extract_ok,
                  );
                  return (
                    <TableRow
                      key={doc.id}
                      className={cn(
                        uncertain && "border-l-2 border-l-warning/60 bg-warning/[0.04]",
                      )}
                    >
                      <TableCell className="max-w-0 min-w-[200px] align-middle">
                        <div className="flex items-center gap-2">
                          <span
                            className="inline-flex shrink-0 text-muted-foreground"
                            title={`${formatBytes(doc.file_size_bytes)} · ${doc.original_name}`}
                          >
                            <FileIcon contentType={doc.content_type} />
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
                      <TableCell className="w-[4.5rem] align-middle">
                        <span className="inline-block rounded bg-muted px-1 py-0 font-mono text-[10px] leading-none text-foreground/75">
                          {mimeLabel(doc.content_type)}
                        </span>
                      </TableCell>
                      <TableCell className="align-middle text-foreground/75">{institutionLabel(doc.bank_code)}</TableCell>
                      <TableCell className="align-middle text-foreground/75">{formatDocPeriod(doc.period)}</TableCell>
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
                      <TableCell className="align-middle">
                        <div className="flex items-center gap-0.5">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleViewDocument(doc)}
                            disabled={viewingId === doc.id}
                            className="text-muted-foreground hover:text-foreground"
                            aria-label={`Visualizar ${doc.original_name}`}
                            title={
                              doc.content_type?.includes("pdf") || doc.content_type?.includes("image/")
                                ? "Abrir no navegador"
                                : "Baixar arquivo"
                            }
                          >
                            {viewingId === doc.id ? (
                              <Spinner size="sm" />
                            ) : doc.content_type?.includes("pdf") ||
                              doc.content_type?.includes("image/") ? (
                              <Eye className="h-4 w-4" />
                            ) : (
                              <Download className="h-4 w-4" />
                            )}
                          </Button>
                          {doc.pipeline_e2_extract_ok ? (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleViewExtract(doc)}
                              disabled={loadingExtractId === doc.id}
                              className="text-muted-foreground hover:text-foreground"
                              aria-label={`Ver JSON extraído de ${doc.original_name}`}
                              title="Ver JSON extraído (E2)"
                            >
                              {loadingExtractId === doc.id ? (
                                <Spinner size="sm" />
                              ) : (
                                <Braces className="h-4 w-4" />
                              )}
                            </Button>
                          ) : (
                            <span className="inline-flex h-8 w-8" aria-hidden />
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setEditTarget(doc)}
                            className="text-muted-foreground hover:text-foreground"
                            aria-label={`Editar classificação de ${doc.original_name}`}
                            title="Editar tipo e instituição"
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setDeleteTarget({ id: doc.id, name: doc.original_name })}
                            className="text-muted-foreground hover:text-destructive"
                            aria-label={`Remover ${doc.original_name}`}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TooltipProvider>
        </div>
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title={`Remover "${deleteTarget?.name}"?`}
        description="O documento será removido permanentemente."
        confirmLabel="Remover"
        variant="destructive"
        onConfirm={handleDelete}
      />

      <EditDocumentDialog
        workspaceId={workspace.id}
        doc={editTarget}
        open={!!editTarget}
        onClose={() => setEditTarget(null)}
        onSaved={(updated) => {
          setDocs((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
          setSuccessMsg("Classificação atualizada.");
        }}
      />

      <Dialog open={!!extractModal} onOpenChange={(open) => !open && setExtractModal(null)}>
        <DialogContent className="max-h-[90vh] w-[90vw] !max-w-[90vw] sm:!max-w-[90vw] flex flex-col">
          <DialogHeader className="shrink-0">
            <DialogTitle className="flex items-center gap-2 font-mono text-sm">
              <Braces className="h-4 w-4 shrink-0" />
              <span className="truncate">{extractModal?.result.filename}</span>
            </DialogTitle>
            {extractModal && extractModal.result.all_candidates.length > 1 && (
              <p className="text-xs text-muted-foreground mt-1">
                {extractModal.result.all_candidates.length} extratos disponíveis —
                exibindo melhor correspondência para{" "}
                <span className="font-mono">{extractModal.doc.bank_code ?? "—"}</span>
                {extractModal.doc.period ? ` · ${extractModal.doc.period}` : ""}
              </p>
            )}
          </DialogHeader>
          <div className="flex-1 overflow-auto rounded border bg-muted/40 p-3">
            <pre className="text-xs font-mono whitespace-pre-wrap break-all leading-relaxed">
              {extractModal ? JSON.stringify(extractModal.result.data, null, 2) : ""}
            </pre>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── SortableHead ────────────────────────────────────────────────────────────

type SortKey = "original_name" | "doc_type" | "content_type" | "bank_code" | "period" | "status" | "uploaded_at";
type SortDir = "asc" | "desc";

function SortableHead({
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
  return (
    <TableHead className={className}>
      <button
        onClick={() => onSort(col)}
        className={`inline-flex items-center gap-1 rounded px-1 -mx-1 py-0.5 text-xs font-medium transition-colors hover:text-foreground select-none ${
          active ? "text-foreground" : "text-muted-foreground"
        }`}
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

function FileIcon({ contentType }: { contentType: string | null }) {
  if (!contentType) return <File className="h-4 w-4" />;
  if (contentType.includes("pdf")) return <FileText className="h-4 w-4" />;
  if (contentType.includes("csv") || contentType.includes("spreadsheet") || contentType.includes("excel"))
    return <FileSpreadsheet className="h-4 w-4" />;
  if (contentType.includes("image")) return <BarChart3 className="h-4 w-4" />;
  if (contentType.includes("json")) return <Wrench className="h-4 w-4" />;
  return <File className="h-4 w-4" />;
}

/** Converts a MIME type string into a short human-readable format label. */
function mimeLabel(contentType: string | null): string {
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
