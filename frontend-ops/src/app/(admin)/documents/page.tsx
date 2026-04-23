"use client";

import { useState } from "react";
import { Button, TextInput } from "@/components/ui";
import { Modal } from "@/components/Modal";
import { api, AdminApiError } from "@/lib/api";
import type { PurgeDocumentsResponse } from "@/lib/types";

type Scope = "user" | "workspace";

export default function DocumentsPage() {
  const [scope, setScope] = useState<Scope>("user");
  const [id, setId] = useState("");
  const [preview, setPreview] = useState<PurgeDocumentsResponse | null>(null);
  const [deleteId, setDeleteId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmWord, setConfirmWord] = useState("");
  const [flash, setFlash] = useState<string | null>(null);

  function scopeBody(): { user_id?: string; workspace_id?: string; preview: boolean } {
    return scope === "user"
      ? { user_id: id.trim(), preview: true }
      : { workspace_id: id.trim(), preview: true };
  }

  async function runPreview(): Promise<void> {
    setError(null);
    setBusy(true);
    setPreview(null);
    try {
      const res = await api.purgeDocuments(scopeBody());
      setPreview(res);
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
      const body = { ...scopeBody(), preview: false };
      const res = await api.purgeDocuments(body);
      setPreview(res);
      setFlash(`Purge concluído: ${res.count} documentos · ${res.blobs_removed ?? 0} blobs.`);
      setConfirmOpen(false);
      setConfirmWord("");
    } catch (err) {
      setError(err instanceof AdminApiError ? `${err.status} · ${err.code}` : "Falha ao executar purge.");
    } finally {
      setBusy(false);
    }
  }

  async function deleteOne(): Promise<void> {
    if (!deleteId.trim()) return;
    setError(null);
    setBusy(true);
    try {
      const res = await api.deleteDocument(deleteId.trim());
      setFlash(`Documento ${res.document_id} excluído · blob ${res.blob_removed ? "removido" : "não encontrado"}.`);
      setDeleteId("");
    } catch (err) {
      if (err instanceof AdminApiError && err.status === 404) {
        setError("Documento não encontrado.");
      } else {
        setError(err instanceof AdminApiError ? `${err.status} · ${err.code}` : "Falha ao excluir.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-10">
      <div>
        <h1 className="font-display text-2xl font-semibold text-surface-fg mb-4">
          Documentos
        </h1>

        {flash && (
          <div className="mb-4 rounded-md border border-semantic-gain/30 bg-semantic-gain/10 text-semantic-gain text-sm px-3 py-2">
            {flash}
          </div>
        )}
        {error && (
          <div className="mb-4 rounded-md border border-brand-danger/30 bg-brand-danger/10 text-brand-danger text-sm px-3 py-2">
            {error}
          </div>
        )}

        <div className="rounded-card border border-surface-border bg-surface-card p-5 space-y-4">
          <h2 className="font-display text-lg text-brand-primary">Purge em massa</h2>
          <p className="text-sm text-surface-muted-fg">
            Sempre peça a prévia antes de confirmar. O backend exige
            <code> user_id </code> ou <code> workspace_id</code>.
          </p>

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
            <div className="rounded-md bg-surface-muted p-4">
              <div className="text-sm text-surface-fg font-medium mb-2">
                {preview.preview ? "Prévia" : "Resultado"}: {preview.count} documento(s)
                {preview.blobs_removed != null && (
                  <span className="text-surface-muted-fg">
                    {" "}· {preview.blobs_removed} blobs removidos
                  </span>
                )}
              </div>
              {preview.ids.length > 0 && (
                <ul className="font-mono text-xs text-surface-muted-fg max-h-64 overflow-y-auto space-y-0.5">
                  {preview.ids.map((docId) => (
                    <li key={docId}>{docId}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </div>

      <div>
        <div className="rounded-card border border-surface-border bg-surface-card p-5 space-y-3">
          <h2 className="font-display text-lg text-brand-primary">Excluir documento individual</h2>
          <div className="flex gap-2">
            <TextInput
              value={deleteId}
              onChange={(e) => setDeleteId(e.target.value)}
              placeholder="document_id"
              className="flex-1"
            />
            <Button variant="danger" onClick={deleteOne} disabled={busy || !deleteId.trim()}>
              Excluir
            </Button>
          </div>
        </div>
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
        <p>
          Vai apagar <strong>{preview?.count ?? 0}</strong> documento(s) e respectivos
          blobs. Digite <code>purge</code> para confirmar.
        </p>
        <TextInput
          value={confirmWord}
          onChange={(e) => setConfirmWord(e.target.value)}
          className="w-full mt-2"
        />
      </Modal>
    </section>
  );
}
