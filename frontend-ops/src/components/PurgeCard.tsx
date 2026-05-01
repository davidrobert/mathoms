"use client";

import { useState, type ReactNode } from "react";
import { Button, TextInput } from "@/components/ui";
import { Modal } from "@/components/Modal";
import { AdminApiError } from "@/lib/api";
import type { ScopeContext } from "@/lib/types";

type Scope = "user" | "workspace";

export interface PurgePreviewBase {
  preview: boolean;
  count: number;
  ids: string[];
  scope_context: ScopeContext | null;
}

interface PurgeCardProps<T extends PurgePreviewBase> {
  title: string;
  helperText: ReactNode;
  confirmCopy: (preview: T) => ReactNode;
  flashCopy: (result: T) => string;
  onPreview: (scope: { user_id?: string; workspace_id?: string; preview: boolean }) => Promise<T>;
  renderPreviewExtras?: (preview: T) => ReactNode;
  renderId?: (id: string, preview: T) => ReactNode;
  onAfterPurge?: () => void;
}

const PAGE_SIZE = 20;

function ContextBlock({ ctx, scope }: { ctx: ScopeContext | null; scope: Scope }) {
  if (!ctx || (!ctx.owner_email && ctx.workspace_names.length === 0)) {
    return (
      <div className="text-xs text-brand-warning-fg">
        ID não corresponde a {scope === "user" ? "usuário" : "workspace"} existente.
      </div>
    );
  }
  return (
    <div className="text-sm text-surface-fg space-y-0.5">
      {ctx.owner_email && (
        <div>
          <span className="text-surface-muted-fg">Dono: </span>
          <strong>{ctx.owner_email}</strong>
        </div>
      )}
      {ctx.workspace_names.length > 0 && (
        <div>
          <span className="text-surface-muted-fg">Workspace(s): </span>
          <strong>{ctx.workspace_names.join(" · ")}</strong>
        </div>
      )}
    </div>
  );
}

export function PurgeCard<T extends PurgePreviewBase>({
  title,
  helperText,
  confirmCopy,
  flashCopy,
  onPreview,
  renderPreviewExtras,
  renderId,
  onAfterPurge,
}: PurgeCardProps<T>) {
  const [scope, setScope] = useState<Scope>("user");
  const [id, setId] = useState("");
  const [preview, setPreview] = useState<T | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmWord, setConfirmWord] = useState("");
  const [flash, setFlash] = useState<string | null>(null);
  const [previewPage, setPreviewPage] = useState(0);

  function scopeBody(p: boolean): { user_id?: string; workspace_id?: string; preview: boolean } {
    return scope === "user"
      ? { user_id: id.trim(), preview: p }
      : { workspace_id: id.trim(), preview: p };
  }

  async function runPreview(): Promise<void> {
    setError(null);
    setBusy(true);
    setPreview(null);
    setPreviewPage(0);
    try {
      setPreview(await onPreview(scopeBody(true)));
    } catch (err) {
      setError(err instanceof AdminApiError ? `${err.status} · ${err.code}` : "Falha ao buscar prévia.");
    } finally {
      setBusy(false);
    }
  }

  async function runPurge(): Promise<void> {
    setError(null);
    setBusy(true);
    try {
      const res = await onPreview(scopeBody(false));
      setPreview(res);
      setFlash(flashCopy(res));
      setConfirmOpen(false);
      setConfirmWord("");
      onAfterPurge?.();
    } catch (err) {
      setError(err instanceof AdminApiError ? `${err.status} · ${err.code}` : "Falha ao executar purge.");
    } finally {
      setBusy(false);
    }
  }

  const idsPage = preview?.ids.slice(previewPage * PAGE_SIZE, (previewPage + 1) * PAGE_SIZE) ?? [];
  const totalPages = preview ? Math.ceil(preview.ids.length / PAGE_SIZE) : 0;

  return (
    <div className="space-y-4">
      {flash && (
        <div className="rounded-md border border-semantic-gain/30 bg-semantic-gain/10 text-semantic-gain text-sm px-3 py-2">
          {flash}
        </div>
      )}
      {error && (
        <div className="rounded-md border border-brand-danger/30 bg-brand-danger/10 text-brand-danger text-sm px-3 py-2">
          {error}
        </div>
      )}

      <div className="rounded-card border border-surface-border bg-surface-card p-5 space-y-4">
        <h2 className="font-display text-lg text-brand-primary">{title}</h2>
        <div className="text-sm text-surface-muted-fg">{helperText}</div>

        <div className="flex flex-wrap gap-3 items-end">
          <label className="text-sm">
            <span className="block mb-1">Escopo</span>
            <select
              value={scope}
              onChange={(e) => setScope(e.target.value as Scope)}
              className="rounded-md border border-surface-border bg-surface-bg px-2 py-2 text-sm"
            >
              <option value="user">user_id</option>
              <option value="workspace">workspace_id</option>
            </select>
          </label>
          <label className="flex-1 text-sm min-w-[260px]">
            <span className="block mb-1">ID</span>
            <TextInput
              value={id}
              onChange={(e) => setId(e.target.value)}
              placeholder={scope === "user" ? "UUID do usuário" : "UUID do workspace"}
              className="w-full"
            />
          </label>
          <Button variant="secondary" onClick={runPreview} disabled={busy || !id.trim()}>
            Prévia
          </Button>
          <Button
            variant="danger"
            onClick={() => setConfirmOpen(true)}
            disabled={busy || !preview || preview.count === 0}
          >
            Confirmar purge
          </Button>
        </div>

        {preview && (
          <div className="rounded-md bg-surface-muted p-4 space-y-3">
            <ContextBlock ctx={preview.scope_context} scope={scope} />
            <div className="text-sm text-surface-fg font-medium">
              {preview.preview ? "Prévia" : "Resultado"}: {preview.count}{" "}
              {preview.count === 1 ? "registro" : "registros"}
            </div>
            {renderPreviewExtras?.(preview)}
            {preview.ids.length > 0 && (
              <>
                <ul className="font-mono text-xs text-surface-muted-fg max-h-64 overflow-y-auto space-y-0.5">
                  {idsPage.map((rowId) => (
                    <li key={rowId} className="py-0.5">
                      {renderId && preview ? renderId(rowId, preview) : rowId}
                    </li>
                  ))}
                </ul>
                {totalPages > 1 && (
                  <div className="flex items-center justify-between text-xs text-surface-muted-fg">
                    <button
                      onClick={() => setPreviewPage((p) => Math.max(0, p - 1))}
                      disabled={previewPage === 0}
                      className="px-2 py-1 rounded hover:bg-surface-border disabled:opacity-40"
                    >
                      Anterior
                    </button>
                    <span>
                      Página {previewPage + 1} de {totalPages}
                    </span>
                    <button
                      onClick={() => setPreviewPage((p) => Math.min(totalPages - 1, p + 1))}
                      disabled={previewPage + 1 >= totalPages}
                      className="px-2 py-1 rounded hover:bg-surface-border disabled:opacity-40"
                    >
                      Próxima
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>

      <Modal
        open={confirmOpen}
        title="Confirmar purge"
        onClose={() => setConfirmOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmOpen(false)}>
              Cancelar
            </Button>
            <Button
              variant="danger"
              onClick={runPurge}
              disabled={busy || confirmWord !== "purge" || !preview}
            >
              {busy ? "Executando…" : "Executar"}
            </Button>
          </>
        }
      >
        {preview && confirmCopy(preview)}
        <p className="text-xs text-brand-warning-fg">
          Operação irreversível. Audit registra a ação mas não permite rollback.
        </p>
        <p>
          Digite <code>purge</code> para confirmar.
        </p>
        <TextInput
          value={confirmWord}
          onChange={(e) => setConfirmWord(e.target.value)}
          className="w-full mt-2"
          autoFocus
        />
      </Modal>
    </div>
  );
}
