"use client";

import { useState } from "react";
import { Button, TextInput } from "@/components/ui";
import { PurgeCard } from "@/components/PurgeCard";
import { api } from "@/lib/api";
import type { AdminReportListResponse, PurgeReportsResponse } from "@/lib/types";
import { useAdminFetch } from "@/lib/use-admin-fetch";

function formatBytes(bytes: number | null): string {
  if (bytes == null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let i = 0;
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024;
    i += 1;
  }
  return `${value.toFixed(1)} ${units[i]}`;
}

const PAGE_SIZE = 25;

interface ReportsQuery {
  user: string;
  workspace: string;
  offset: number;
}

function fetchReports(query: ReportsQuery): Promise<AdminReportListResponse> {
  return api.listReports({
    user_id: query.user.trim() || undefined,
    workspace_id: query.workspace.trim() || undefined,
    limit: PAGE_SIZE,
    offset: query.offset,
  });
}

export default function ReportsPage() {
  const [userId, setUserId] = useState("");
  const [workspaceId, setWorkspaceId] = useState("");
  const [query, setQuery] = useState<ReportsQuery>({ user: "", workspace: "", offset: 0 });
  const { data, loading, error } = useAdminFetch(query, fetchReports, "Falha ao carregar.");
  const reports = data?.reports ?? [];
  const total = data?.total ?? 0;
  const { offset } = query;

  return (
    <section className="space-y-10">
      <div>
        <h1 className="font-display text-2xl font-semibold text-surface-fg mb-4">Relatórios</h1>
        <PurgeCard<PurgeReportsResponse>
          title="Purge em massa"
          helperText={
            <>
              Apaga relatórios, anotações (T6), itens do Kanban (T3) e o artefato E5 do pipeline
              (análise) referenciado por cada relatório. Outros stages (E2/E3/E4) e os documentos
              originais permanecem intactos. Peça a prévia antes de confirmar.
            </>
          }
          onPreview={api.purgeReports}
          renderPreviewExtras={(p) =>
            p.preview ? (
              <div className="text-xs text-surface-muted-fg">
                {p.artifacts_to_remove} artefato(s) E5 também serão apagados.
              </div>
            ) : (
              <div className="text-xs text-surface-muted-fg">
                {p.artifacts_removed ?? 0} artefato(s) E5 removidos.
              </div>
            )
          }
          confirmCopy={(p) => (
            <p>
              Vai apagar <strong>{p.count}</strong> relatório(s) e{" "}
              <strong>{p.artifacts_to_remove}</strong> artefato(s) E5
              {p.scope_context?.workspace_names.length
                ? ` do workspace ${p.scope_context.workspace_names.join(" / ")}`
                : ""}
              .
            </p>
          )}
          flashCopy={(p) =>
            `Purge concluído: ${p.count} relatórios · ${p.artifacts_removed ?? 0} artefatos E5.`
          }
          // Cópia = pedido novo: useAdminFetch compara a query por identidade.
          onAfterPurge={() => setQuery((current) => ({ ...current }))}
        />
      </div>

      <div>
        <div className="flex items-end justify-between gap-4 mb-6">
          <div>
            <h2 className="font-display text-lg font-semibold text-surface-fg">Listing</h2>
            <p className="text-sm text-surface-muted-fg">
              Read-only. {total.toLocaleString("pt-BR")} resultado(s) · exibindo {reports.length}.
            </p>
          </div>
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              setQuery({ user: userId, workspace: workspaceId, offset: 0 });
            }}
          >
            <TextInput
              placeholder="user_id"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              className="w-56"
            />
            <TextInput
              placeholder="workspace_id"
              value={workspaceId}
              onChange={(e) => setWorkspaceId(e.target.value)}
              className="w-56"
            />
            <Button variant="secondary" type="submit">
              Filtrar
            </Button>
          </form>
        </div>

        {error && (
          <div className="mb-4 rounded-md border border-brand-danger/30 bg-brand-danger/10 text-brand-danger text-sm px-3 py-2">
            {error}
          </div>
        )}

        <div className="overflow-x-auto border border-surface-border rounded-card bg-surface-card">
          <table className="w-full text-sm">
            <thead className="bg-surface-muted text-surface-muted-fg">
              <tr>
                <th className="text-left px-4 py-2 font-medium">Título</th>
                <th className="text-left px-4 py-2 font-medium">Usuário</th>
                <th className="text-left px-4 py-2 font-medium">Workspace</th>
                <th className="text-left px-4 py-2 font-medium">Período</th>
                <th className="text-left px-4 py-2 font-medium">Criado</th>
                <th className="text-right px-4 py-2 font-medium">Tamanho</th>
                <th className="text-right px-4 py-2 font-medium">Abrir</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={7} className="px-4 py-6 text-center text-surface-muted-fg">
                    Carregando…
                  </td>
                </tr>
              )}
              {!loading && reports.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-6 text-center text-surface-muted-fg">
                    Nenhum relatório.
                  </td>
                </tr>
              )}
              {reports.map((r) => (
                <tr key={r.id} className="border-t border-surface-border">
                  <td className="px-4 py-2 text-surface-fg">{r.title}</td>
                  <td className="px-4 py-2 text-surface-muted-fg">
                    {r.owner_email ?? <span className="italic text-surface-muted-fg">—</span>}
                  </td>
                  <td
                    className="px-4 py-2 font-mono text-xs text-surface-muted-fg"
                    title={r.workspace_name ?? undefined}
                  >
                    {r.workspace_name ? (
                      <span className="text-surface-fg block">{r.workspace_name}</span>
                    ) : null}
                    <span className="block">{r.workspace_id}</span>
                  </td>
                  <td className="px-4 py-2 text-surface-muted-fg">{r.period ?? "—"}</td>
                  <td className="px-4 py-2 text-surface-muted-fg">
                    {new Date(r.created_at).toLocaleString("pt-BR")}
                  </td>
                  <td className="px-4 py-2 text-right mono-num text-surface-muted-fg">
                    {formatBytes(r.size_bytes)}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <a
                      href={`/admin/reports/${r.id}/html`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-brand-primary hover:underline text-sm"
                      title="HTML read-only via ops_session — não exige login do usuário"
                    >
                      abrir ↗
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {total > PAGE_SIZE && (
          <div className="mt-4 flex items-center justify-between text-sm text-surface-muted-fg">
            <Button
              variant="secondary"
              onClick={() =>
                setQuery((current) => ({ ...current, offset: Math.max(0, current.offset - PAGE_SIZE) }))
              }
              disabled={offset === 0 || loading}
            >
              Anterior
            </Button>
            <span>
              {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} de {total}
            </span>
            <Button
              variant="secondary"
              onClick={() => setQuery((current) => ({ ...current, offset: current.offset + PAGE_SIZE }))}
              disabled={offset + PAGE_SIZE >= total || loading}
            >
              Próxima
            </Button>
          </div>
        )}
      </div>
    </section>
  );
}
