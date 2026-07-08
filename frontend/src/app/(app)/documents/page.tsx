"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
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
import { isDocumentClassifiedOk } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import { Spinner } from "@/components/Spinner";
import { EmptyState } from "@/components/EmptyState";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { EditDocumentDialog } from "@/components/EditDocumentDialog";
import { Button } from "@/components/ui/button";
import { useWorkspace } from "@/lib/WorkspaceProvider";
import type { UserWorkspace } from "@/lib/api";

import { UploadZone } from "./_components/UploadZone";
import { NeedsPasswordBanner } from "./_components/NeedsPasswordBanner";
import { FilterReclassifyBar } from "./_components/FilterReclassifyBar";
import { DocumentsTable } from "./_components/DocumentsTable";
import { ExtractJsonModal } from "./_components/ExtractJsonModal";
import { PendingReviewQueue } from "./_components/PendingReviewQueue";
import { isClassificationUncertain } from "./_components/classificationHints";
import { sortDocs } from "./_components/sortDocs";
import type { SortDir, SortKey } from "./_components/SortableHead";

export default function DocumentsPage() {
  const { workspace } = useWorkspace();
  if (!workspace) return null;
  // Suspense exigido pelo useSearchParams (deep-link ?filter=needs_review,
  // A28.l9 — CTA do ReportDataQualityBanner).
  return (
    <Suspense fallback={null}>
      <DocumentsPageContent workspace={workspace} />
    </Suspense>
  );
}

function MessageBanner({
  kind,
  message,
  onDismiss,
}: {
  kind: "error" | "success";
  message: string;
  onDismiss: () => void;
}) {
  if (!message) return null;
  const cls = kind === "error" ? "bg-loss/10 text-loss" : "bg-gain/10 text-gain";
  return (
    <div className={`mb-4 rounded-lg p-3 text-sm ${cls}`}>
      {message}
      <button onClick={onDismiss} className="ml-2 font-medium underline">
        fechar
      </button>
    </div>
  );
}

function DocumentsPageContent({ workspace }: { workspace: UserWorkspace }) {
  const [docs, setDocs] = useState<DocumentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);
  const [editTarget, setEditTarget] = useState<DocumentResponse | null>(null);
  const [reclassifying, setReclassifying] = useState(false);
  const [viewingId, setViewingId] = useState<string | null>(null);
  // A29.l3 (ADR-308 §8): lote = sequencial "N de M", nunca valor único em massa.
  // O EditDocumentDialog chama onClose logo após onSaved — o ref distingue
  // avanço de fila de cancelamento do usuário.
  const [fixQueue, setFixQueue] = useState<string[]>([]);
  const advancingQueueRef = useRef(false);
  const [queueRefresh, setQueueRefresh] = useState(0);

  const [sortKey, setSortKey] = useState<SortKey>("uploaded_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  // A28.l9 — deep-link do banner de qualidade de dados do relatório.
  const searchParams = useSearchParams();
  const [reviewFilter, setReviewFilter] = useState<"all" | "uncertain">(
    searchParams.get("filter") === "needs_review" ? "uncertain" : "all",
  );
  // A32.l6 PR3 — deep-link "Ver documento" da tela de review (?doc=<id>):
  // abre o EditDocumentDialog do documento assim que a lista carrega.
  const deepLinkDocId = searchParams.get("doc");
  const deepLinkHandledRef = useRef(false);
  const [extractModal, setExtractModal] = useState<{
    doc: DocumentResponse;
    result: ExtractJsonResponse;
  } | null>(null);
  const [loadingExtractId, setLoadingExtractId] = useState<string | null>(null);

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  const sortedDocs = sortDocs(docs, sortKey, sortDir);
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
      const data = await listDocuments(workspace.id);
      setDocs(data.documents);
    } catch {
      setError("Erro ao carregar documentos");
    } finally {
      setLoading(false);
    }
  }, [workspace.id]);

  useEffect(() => {
    reload();
  }, [reload]);

  useEffect(() => {
    if (deepLinkHandledRef.current || !deepLinkDocId || docs.length === 0) return;
    const doc = docs.find((d) => d.id === deepLinkDocId);
    if (doc) {
      deepLinkHandledRef.current = true;
      setEditTarget(doc);
    }
  }, [deepLinkDocId, docs]);

  async function handleUpload(files: FileList | File[]) {
    const fileArray = Array.from(files);
    if (fileArray.length === 0) return;

    setError("");
    setSuccessMsg("");
    setUploading(true);
    setUploadProgress(0);

    try {
      const result = await uploadDocuments(workspace.id, fileArray, (loaded, total) => {
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
        err instanceof ApiError ? err.detail : "Erro ao enviar arquivos. Tente novamente.",
      );
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    try {
      await deleteDocument(workspace.id, deleteTarget.id);
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
      const result = await reclassifyDocuments(workspace.id);
      setSuccessMsg(
        `Reclassificação concluída: ${result.updated} atualizado(s), ${result.skipped} ignorado(s)${
          result.errors > 0 ? `, ${result.errors} com erro` : ""
        }.`,
      );
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao reclassificar documentos");
    } finally {
      setReclassifying(false);
    }
  }

  async function openFileInBrowser(blob: Blob, filename: string, contentType: string) {
    const url = URL.createObjectURL(blob);
    const isInlineable = contentType.includes("pdf") || contentType.includes("image/");
    if (isInlineable) {
      const tab = window.open(url, "_blank");
      if (tab) {
        setTimeout(() => URL.revokeObjectURL(url), 60_000);
      } else {
        URL.revokeObjectURL(url);
        setError("O popup foi bloqueado. Permita popups para este site e tente novamente.");
      }
    } else {
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  }

  async function handleViewDocument(doc: DocumentResponse) {
    if (viewingId) return;
    setViewingId(doc.id);
    setError("");
    try {
      const { blob, filename, contentType } = await fetchDocumentFile(workspace.id, doc.id);
      await openFileInBrowser(blob, filename, contentType);
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
      const result = await retryUnlock(workspace.id);
      const unlocked = result.filter((d) => d.status === "ready").length;
      setSuccessMsg(
        unlocked > 0
          ? `${unlocked} documento(s) desbloqueado(s)!`
          : "Nenhum documento conseguiu ser desbloqueado.",
      );
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao tentar desbloquear");
    }
  }

  const generateReportAction =
    readyDocs.length > 0 ? (
      <Button nativeButton={false} render={<Link href="/pipeline" />}>
        Gerar Relatório ({readyDocs.length} doc{readyDocs.length > 1 ? "s" : ""})
      </Button>
    ) : undefined;

  return (
    <div className="mx-auto max-w-content px-6 py-8">
      <PageHeader
        title="Documentos"
        description="Envie extratos, faturas e documentos financeiros"
        actions={generateReportAction}
      />

      <MessageBanner kind="error" message={error} onDismiss={() => setError("")} />
      <MessageBanner kind="success" message={successMsg} onDismiss={() => setSuccessMsg("")} />

      <UploadZone
        fileInputRef={fileInputRef}
        uploading={uploading}
        uploadProgress={uploadProgress}
        onSelect={handleUpload}
      />

      <NeedsPasswordBanner count={needsPasswordDocs.length} onRetry={handleRetryUnlock} />

      <PendingReviewQueue
        workspaceId={workspace.id}
        docs={docs}
        refreshKey={queueRefresh}
        onFixDocument={(documentId) => {
          const doc = docs.find((d) => d.id === documentId);
          if (doc) setEditTarget(doc);
        }}
        onFixSequence={(documentIds) => {
          const [first, ...rest] = documentIds;
          const doc = docs.find((d) => d.id === first);
          if (doc) {
            setFixQueue(rest);
            setEditTarget(doc);
          }
        }}
      />

      {!loading && docs.length > 0 && (
        <FilterReclassifyBar
          totalDocs={docs.length}
          uncertainCount={uncertainClassificationDocs.length}
          reviewFilter={reviewFilter}
          onToggleFilter={() =>
            setReviewFilter((f) => (f === "uncertain" ? "all" : "uncertain"))
          }
          reclassifying={reclassifying}
          onReclassify={handleReclassify}
        />
      )}

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
        <DocumentsTable
          docs={displayedDocs}
          sortKey={sortKey}
          sortDir={sortDir}
          onSort={handleSort}
          viewingId={viewingId}
          loadingExtractId={loadingExtractId}
          onView={handleViewDocument}
          onViewExtract={handleViewExtract}
          onEdit={setEditTarget}
          onRequestDelete={(d) => setDeleteTarget({ id: d.id, name: d.original_name })}
        />
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
        onClose={() => {
          if (advancingQueueRef.current) {
            advancingQueueRef.current = false;
            return;
          }
          setEditTarget(null);
          if (fixQueue.length > 0) setFixQueue([]);
        }}
        onSaved={(updated) => {
          setDocs((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
          const [next, ...rest] = fixQueue;
          const nextDoc = next ? docs.find((d) => d.id === next) : undefined;
          if (nextDoc) {
            advancingQueueRef.current = true;
            setFixQueue(rest);
            setEditTarget(nextDoc);
            setSuccessMsg(
              `Classificação atualizada. Próximo documento (faltam ${rest.length + 1}).`,
            );
          } else {
            setFixQueue([]);
            setSuccessMsg("Classificação atualizada.");
            setQueueRefresh((k) => k + 1);
          }
        }}
      />

      <ExtractJsonModal data={extractModal} onClose={() => setExtractModal(null)} />
    </div>
  );
}
