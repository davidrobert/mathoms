"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  listDocuments,
  uploadDocuments,
  deleteDocument,
  retryUnlock,
  type DocumentResponse,
  ApiError,
} from "@/lib/api";
import {
  formatBytes,
  formatDate,
  formatDocPeriod,
  docStatusLabel,
  docTypeLabel,
  fileFormatLabel,
  institutionLabel,
  pipelineE2TouchLabel,
} from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { Spinner } from "@/components/Spinner";
import { EmptyState } from "@/components/EmptyState";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
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
} from "lucide-react";
import { useWorkspace } from "@/lib/WorkspaceProvider";

export default function DocumentsPage() {
  const { workspace } = useWorkspace();
  if (!workspace) return null;

  const [docs, setDocs] = useState<DocumentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);

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
      const readyCount = uploaded.filter((d) => d.status === "ready").length;
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

  const needsPasswordDocs = docs.filter((d) => d.status === "needs_password");
  const readyDocs = docs.filter((d) => d.status === "ready");

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
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
        <div className="overflow-x-auto rounded-xl border border-border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Arquivo</TableHead>
                <TableHead>Formato</TableHead>
                <TableHead>Tipo</TableHead>
                <TableHead>Instituição</TableHead>
                <TableHead>Período</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Último pipeline</TableHead>
                <TableHead>Tamanho</TableHead>
                <TableHead>Data</TableHead>
                <TableHead className="w-10"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {docs.map((doc) => {
                const st = docStatusLabel(doc.status);
                return (
                  <TableRow key={doc.id}>
                    <TableCell className="max-w-[200px] truncate font-medium" title={doc.original_name}>
                      <span className="mr-2 inline-flex text-muted-foreground">
                        <FileIcon contentType={doc.content_type} />
                      </span>
                      {doc.original_name}
                    </TableCell>
                    <TableCell className="text-muted-foreground font-mono text-xs">
                      {fileFormatLabel(doc.content_type, doc.original_name)}
                    </TableCell>
                    <TableCell className="text-muted-foreground">{docTypeLabel(doc.doc_type)}</TableCell>
                    <TableCell className="text-muted-foreground">{institutionLabel(doc.bank_code)}</TableCell>
                    <TableCell className="text-muted-foreground">{formatDocPeriod(doc.period)}</TableCell>
                    <TableCell>
                      <StatusBadge variant={st.variant}>{st.label}</StatusBadge>
                      {doc.error_message && (
                        <span className="ml-1 cursor-help text-muted-foreground" title={doc.error_message}>
                          <Info className="inline h-3.5 w-3.5" />
                        </span>
                      )}
                    </TableCell>
                    <TableCell
                      className="max-w-[160px] text-muted-foreground text-xs"
                      title={
                        doc.pipeline_last_run_at
                          ? "Data do último pipeline concluído com sucesso neste workspace. “Sem extrato E2” indica que não há JSON do estágio E2 para este arquivo (parser não cobriu, só LLM, ou formato não suportado)."
                          : undefined
                      }
                    >
                      {pipelineE2TouchLabel(doc.pipeline_last_run_at, doc.pipeline_e2_extract_ok)}
                    </TableCell>
                    <TableCell className="text-muted-foreground font-mono text-xs">{formatBytes(doc.file_size_bytes)}</TableCell>
                    <TableCell className="text-muted-foreground">{formatDate(doc.uploaded_at)}</TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setDeleteTarget({ id: doc.id, name: doc.original_name })}
                        className="text-muted-foreground hover:text-destructive"
                        aria-label={`Remover ${doc.original_name}`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
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
    </div>
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
