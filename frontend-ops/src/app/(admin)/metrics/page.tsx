"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui";
import { api, AdminApiError } from "@/lib/api";
import { LlmBudgetSection } from "./llm-budget-section";
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

function breakdownRows(prefix: string, counts: Record<string, number>): Array<[string, string]> {
  return Object.entries(counts).map(([k, v]) => [`${prefix}.${k}`, String(v)]);
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
    // A40.l18 — número novo que não entre aqui produz export silenciosamente
    // incompleto; os breakdowns entram achatados como `chave.subchave`.
    ...breakdownRows("pipeline_runs_by_status", snap.pipeline_runs_by_status),
    ...breakdownRows("stages_degraded_by_reason", snap.stages_degraded_by_reason),
    ...breakdownRows("stages_degraded_by_stage", snap.stages_degraded_by_stage),
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

      {snap && <DegradationSection snap={snap} />}

      <LlmBudgetSection />
    </section>
  );
}

/** A40.l18 · ADR-357 — degradação precisa de superfície de PULL, não só de log. */
function DegradationSection({ snap }: { snap: MetricsResponse }) {
  const degraded = sumOf(snap.stages_degraded_by_reason);
  const runs = snap.pipeline_runs_last_period;
  // Taxa, não só contagem: 4 degradações em 200 runs e em 5 runs são mundos
  // diferentes, e sem denominador não existe threshold de investigação.
  const rate = runs > 0 ? `${((degraded / runs) * 100).toFixed(1).replace(".", ",")}%` : "—";
  return (
    <div className="mt-8">
      <h2 className="font-display text-lg font-semibold text-surface-fg">
        Degradação de etapas ({snap.period_days}d)
      </h2>
      <p className="mt-1 text-sm text-surface-muted-fg">
        Etapas que terminaram sem entregar. O relatório foi gerado; a lacuna está declarada.
        Não fecha com os runs abaixo — um run pode degradar várias etapas.
      </p>
      <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
        <KpiCard label="Etapas degradadas" value={degraded.toLocaleString("pt-BR")} />
        <KpiCard label="Taxa sobre runs" value={rate} />
      </div>
      <div className="mt-4 grid gap-6 md:grid-cols-3">
        <CountTable title="Por motivo" counts={snap.stages_degraded_by_reason} />
        <CountTable title="Por etapa" counts={snap.stages_degraded_by_stage} />
        <CountTable title="Runs por desfecho" counts={snap.pipeline_runs_by_status} />
      </div>
    </div>
  );
}

function sumOf(counts: Record<string, number>): number {
  return Object.values(counts).reduce((a, b) => a + b, 0);
}

/** Ordena por frequência e mantém o zero visível — zero medido não é ausência. */
function CountTable({ title, counts }: { title: string; counts: Record<string, number> }) {
  const rows = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  return (
    <div className="rounded-card border border-surface-border bg-surface-card p-4">
      <div className="text-xs uppercase tracking-wide text-surface-muted-fg">{title}</div>
      {rows.length === 0 ? (
        <div className="mt-2 text-sm text-surface-muted-fg">Sem dados na janela.</div>
      ) : (
        <ul className="mt-2 space-y-1 text-sm">
          {rows.map(([k, v]) => (
            <li key={k} className="flex items-baseline justify-between gap-3">
              <span className={v === 0 ? "text-surface-muted-fg" : "text-surface-fg"}>{k}</span>
              <span className="mono-num text-surface-fg">{v.toLocaleString("pt-BR")}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
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
