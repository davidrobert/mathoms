"use client";

import { useState } from "react";
import { Button, TextInput } from "@/components/ui";
import { PurgeCard } from "@/components/PurgeCard";
import { api, AdminApiError } from "@/lib/api";
import type { PurgeDocumentsResponse } from "@/lib/types";

export default function DocumentsPage() {
  const [deleteId, setDeleteId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);

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
        <h1 className="font-display text-2xl font-semibold text-surface-fg mb-4">Documentos</h1>

        <PurgeCard<PurgeDocumentsResponse>
          title="Purge em massa"
          helperText={
            <>
              Apaga documentos, blobs físicos e <strong>todos os pipeline_runs</strong> do escopo
              (cascade limpa artefatos derivados E2/E3/E4/E5, stage logs e revisões). Sempre peça a
              prévia antes de confirmar.
            </>
          }
          onPreview={api.purgeDocuments}
          renderPreviewExtras={(p) =>
            p.preview ? (
              <div className="text-xs text-surface-muted-fg">
                {p.runs_to_remove} pipeline_run(s) e respectivos artefatos serão apagados.
              </div>
            ) : (
              <div className="text-xs text-surface-muted-fg">
                {p.blobs_removed ?? 0} blobs · {p.runs_removed ?? 0} pipeline_run(s) removidos.
              </div>
            )
          }
          renderId={(id, p) => {
            const name = p.items?.find((it) => it.id === id)?.name;
            return name ? (
              <span className="flex flex-wrap gap-x-2">
                <span className="text-surface-fg">{name}</span>
                <span className="text-surface-muted-fg">{id}</span>
              </span>
            ) : (
              id
            );
          }}
          confirmCopy={(p) => (
            <p>
              Vai apagar <strong>{p.count}</strong> documento(s),{" "}
              <strong>{p.runs_to_remove}</strong> pipeline_run(s) e respectivos artefatos
              {p.scope_context?.workspace_names.length
                ? ` do workspace ${p.scope_context.workspace_names.join(" / ")}`
                : ""}
              .
            </p>
          )}
          flashCopy={(p) =>
            `Purge concluído: ${p.count} documentos · ${p.blobs_removed ?? 0} blobs · ${p.runs_removed ?? 0} runs.`
          }
        />
      </div>

      <div>
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
    </section>
  );
}
