"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui";
import { api, AdminApiError } from "@/lib/api";
import type { MetricsResponse } from "@/lib/types";

const PERIODS: ReadonlyArray<{ label: string; days: number }> = [
  { label: "7d", days: 7 },
  { label: "30d", days: 30 },
  { label: "90d", days: 90 },
];

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let value = bytes / 1024;
  let i = 0;
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024;
    i += 1;
  }
  return `${value.toFixed(2)} ${units[i]}`;
}

function downloadCsv(snap: MetricsResponse): void {
  const rows: Array<[string, string]> = [
    ["users_total", String(snap.users_total)],
    ["users_active", String(snap.users_active)],
    ["workspaces_total", String(snap.workspaces_total)],
    ["documents_total", String(snap.documents_total)],
    ["documents_needs_review", String(snap.documents_needs_review)],
    ["storage_bytes_total", String(snap.storage_bytes_total)],
    ["pipeline_runs_total", String(snap.pipeline_runs_total)],
    ["pipeline_runs_last_period", String(snap.pipeline_runs_last_period)],
    ["documents_uploaded_last_period", String(snap.documents_uploaded_last_period)],
    ["new_users_last_period", String(snap.new_users_last_period)],
    ["period_days", String(snap.period_days)],
    ["generated_at", snap.generated_at],
  ];
  const csv = "metric,value\n" + rows.map(([k, v]) => `${k},${v}`).join("\n") + "\n";
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `mathoms-metrics-${snap.period_days}d.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export default function MetricsPage() {
  const [days, setDays] = useState(30);
  const [snap, setSnap] = useState<MetricsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (periodDays: number): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getMetrics(periodDays);
      setSnap(res);
    } catch (err) {
      setError(err instanceof AdminApiError ? `${err.status} · ${err.code}` : "Falha ao carregar métricas.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(days);
  }, [load, days]);

  return (
    <section>
      <div className="flex items-end justify-between mb-6">
        <div>
          <h1 className="font-display text-2xl font-semibold text-surface-fg">Métricas</h1>
          <p className="text-sm text-surface-muted-fg">
            {snap ? `Gerado em ${new Date(snap.generated_at).toLocaleString("pt-BR")}` : "—"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="inline-flex rounded-md border border-surface-border overflow-hidden">
            {PERIODS.map((p) => (
              <button
                key={p.days}
                onClick={() => setDays(p.days)}
                className={`px-3 py-1.5 text-sm ${
                  days === p.days
                    ? "bg-brand-primary text-brand-primary-fg"
                    : "bg-surface-card text-surface-fg hover:bg-surface-muted"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
          <Button variant="secondary" onClick={() => snap && downloadCsv(snap)} disabled={!snap}>
            Exportar CSV
          </Button>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-md border border-brand-danger/30 bg-brand-danger/10 text-brand-danger text-sm px-3 py-2">
          {error}
        </div>
      )}

      {loading && <p className="text-surface-muted-fg">Carregando…</p>}

      {snap && !loading && (
        <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
          <KpiCard label="Usuários (total)" value={snap.users_total.toLocaleString("pt-BR")} />
          <KpiCard label="Usuários ativos" value={snap.users_active.toLocaleString("pt-BR")} />
          <KpiCard label="Workspaces" value={snap.workspaces_total.toLocaleString("pt-BR")} />
          <KpiCard label="Documentos" value={snap.documents_total.toLocaleString("pt-BR")} />
          <KpiCard
            label="Needs review"
            value={snap.documents_needs_review.toLocaleString("pt-BR")}
          />
          <KpiCard label="Storage total" value={formatBytes(snap.storage_bytes_total)} />
          <KpiCard
            label="Runs (total)"
            value={snap.pipeline_runs_total.toLocaleString("pt-BR")}
          />
          <KpiCard
            label={`Runs (${snap.period_days}d)`}
            value={snap.pipeline_runs_last_period.toLocaleString("pt-BR")}
          />
          <KpiCard
            label={`Uploads (${snap.period_days}d)`}
            value={snap.documents_uploaded_last_period.toLocaleString("pt-BR")}
          />
          <KpiCard
            label={`Novos users (${snap.period_days}d)`}
            value={snap.new_users_last_period.toLocaleString("pt-BR")}
          />
        </div>
      )}
    </section>
  );
}

function KpiCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-card border border-surface-border bg-surface-card p-4">
      <div className="text-xs uppercase tracking-wide text-surface-muted-fg">{label}</div>
      <div className="mt-1 font-display text-2xl font-semibold text-brand-primary mono-num">
        {value}
      </div>
    </div>
  );
}
