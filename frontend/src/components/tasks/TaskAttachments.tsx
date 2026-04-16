"use client";

/**
 * Lista + upload + delete de anexos de uma task (F8.3).
 *
 * Integra no TaskDrawer. Usa download direto via href (o endpoint serve
 * FileResponse com Content-Disposition derivado do original_filename).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Download, Paperclip, Trash2, Upload, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import {
  deleteTaskAttachment,
  listTaskAttachments,
  taskAttachmentDownloadUrl,
  uploadTaskAttachment,
  ApiError,
  type TaskAttachmentMeta,
} from "@/lib/api";


interface TaskAttachmentsProps {
  workspaceId: string;
  taskId: string;
}


function formatSize(bytes: number | null): string {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}


export function TaskAttachments({
  workspaceId,
  taskId,
}: TaskAttachmentsProps) {
  const [items, setItems] = useState<TaskAttachmentMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await listTaskAttachments(workspaceId, taskId);
      setItems(resp.attachments);
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
      else setError("Erro ao carregar anexos");
    } finally {
      setLoading(false);
    }
  }, [workspaceId, taskId]);

  useEffect(() => {
    reload();
  }, [reload]);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      await uploadTaskAttachment(workspaceId, taskId, file);
      await reload();
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
      else setError("Erro ao enviar arquivo");
    } finally {
      setUploading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  async function handleDelete(attachment: TaskAttachmentMeta) {
    if (!confirm(`Remover "${attachment.original_filename}"?`)) return;
    setDeletingId(attachment.id);
    try {
      await deleteTaskAttachment(workspaceId, taskId, attachment.id);
      await reload();
    } catch (err) {
      if (err instanceof ApiError) alert(err.detail);
      else alert("Erro ao remover anexo");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
          <Paperclip className="h-3 w-3" />
          Anexos
          {items.length > 0 && (
            <span className="tabular-nums">({items.length})</span>
          )}
        </span>
        <Button
          size="xs"
          variant="outline"
          onClick={() => fileInput.current?.click()}
          disabled={uploading}
        >
          <Upload className="mr-1 h-3 w-3" />
          {uploading ? "Enviando..." : "Anexar"}
        </Button>
        <input
          ref={fileInput}
          type="file"
          className="hidden"
          onChange={handleUpload}
          aria-label="Arquivo para anexar"
        />
      </div>

      {loading ? (
        <Skeleton className="h-10 w-full" />
      ) : error ? (
        <p className="text-xs text-destructive">{error}</p>
      ) : items.length === 0 ? (
        <p className="rounded-md border border-dashed p-3 text-center text-xs text-muted-foreground">
          Nenhum anexo. Clique em &quot;Anexar&quot; para enviar
          comprovantes, contratos ou notas.
        </p>
      ) : (
        <ul className="space-y-1.5">
          {items.map((att) => (
            <li
              key={att.id}
              className={cn(
                "flex items-center gap-2 rounded-md border px-2 py-1.5 text-sm",
                deletingId === att.id && "opacity-50"
              )}
            >
              <Paperclip className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              <span className="flex-1 truncate" title={att.original_filename}>
                {att.original_filename}
              </span>
              <span className="shrink-0 text-xs text-muted-foreground tabular-nums">
                {formatSize(att.size_bytes)}
              </span>
              <a
                href={taskAttachmentDownloadUrl(workspaceId, taskId, att.id)}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                aria-label={`Baixar ${att.original_filename}`}
              >
                <Download className="h-3.5 w-3.5" />
              </a>
              <button
                type="button"
                onClick={() => handleDelete(att)}
                disabled={deletingId === att.id}
                className="inline-flex items-center rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                aria-label={`Remover ${att.original_filename}`}
              >
                {deletingId === att.id ? (
                  <X className="h-3.5 w-3.5 animate-pulse" />
                ) : (
                  <Trash2 className="h-3.5 w-3.5" />
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
