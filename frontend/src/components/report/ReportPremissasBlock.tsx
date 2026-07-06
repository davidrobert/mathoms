"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import type { ReportAnalysisData } from "@/lib/api";
import { REPORT_FORMULA_CATALOG } from "@/lib/reportFormulas";
import { cn } from "@/lib/cn";

/** A28.l9 — snapshot de premissas das metas em formato legível.
 *
 * Substitui o `JSON.stringify` cru que vazava no relatório. Shape produzido
 * por `backend/app/services/premissas_snapshot.py`: `captured_at`,
 * `goals_json_sha256`, `active_goals[{type, id, effective_from}]`. Campos
 * ausentes degradam silenciosamente (snapshot é `Record<string, unknown>`).
 */
function PremissasSnapshotSummary({ snapshot }: { snapshot: Record<string, unknown> }) {
  const capturedAt =
    typeof snapshot.captured_at === "string" ? formatSnapshotDate(snapshot.captured_at) : null;
  const hash =
    typeof snapshot.goals_json_sha256 === "string" ? snapshot.goals_json_sha256 : null;
  const goalTypes = extractActiveGoalTypes(snapshot.active_goals);
  return (
    <div>
      <p className="font-medium text-[var(--surface-foreground)]">
        Snapshot de premissas das metas (referência interna)
      </p>
      <ul className="mt-1 list-disc space-y-0.5 pl-4">
        {capturedAt && <li>Capturado em {capturedAt}</li>}
        <li>
          {goalTypes.length > 0
            ? `${goalTypes.length} ${goalTypes.length === 1 ? "meta ativa" : "metas ativas"}: ${goalTypes.join(", ")}`
            : "Sem metas ativas no momento da geração"}
        </li>
        {hash && (
          <li>
            Integridade:{" "}
            <span className="font-mono tabular-nums">{hash.slice(0, 12)}…</span>
          </li>
        )}
      </ul>
    </div>
  );
}

function extractActiveGoalTypes(activeGoals: unknown): string[] {
  if (!Array.isArray(activeGoals)) return [];
  const types = activeGoals
    .map((g) =>
      typeof g === "object" && g !== null && typeof (g as { type?: unknown }).type === "string"
        ? ((g as { type: string }).type)
        : null,
    )
    .filter((t): t is string => t !== null);
  return [...new Set(types)];
}

function formatSnapshotDate(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
}

/** F11.6c + F11.7 — bloco colapsável de premissas e referência a regras. */
export function ReportPremissasBlock({ data }: { data: ReportAnalysisData }) {
  const [glossaryOpen, setGlossaryOpen] = useState(false);
  const goals = data.goals as Record<string, unknown> | undefined;
  const premissasSnapshot =
    goals && typeof goals === "object" && goals.premissas_snapshot != null
      ? (goals.premissas_snapshot as Record<string, unknown>)
      : null;

  return (
    <section
      className="mb-6 text-xs"
      aria-labelledby="report-premissas-heading"
    >
      <details className="group">
        <summary
          className="flex cursor-pointer list-none items-center gap-1.5 text-[var(--surface-muted-foreground)] hover:text-[var(--surface-foreground)] marker:content-none"
          id="report-premissas-heading"
        >
          <ChevronDown className="h-3 w-3 shrink-0 transition group-open:rotate-180" />
          <span>Premissas e como calculamos</span>
        </summary>
        <div className="mt-2 space-y-2 rounded-md border border-[var(--surface-border)] bg-[color-mix(in_srgb,var(--surface-muted)_25%,transparent)] px-3 py-2.5 leading-relaxed text-[var(--surface-muted-foreground)]">
          <p>
            <span className="font-medium text-[var(--surface-foreground)]">Período dos dados:</span>{" "}
            {String(data.periodo_dados ?? "—")}
          </p>
          <p>
            <span className="font-medium text-[var(--surface-foreground)]">Data da análise:</span>{" "}
            {String(data.data_analise ?? "—")}
          </p>
          {premissasSnapshot && (
            <PremissasSnapshotSummary snapshot={premissasSnapshot} />
          )}
          <p>
            Os KPIs deste relatório refletem o snapshot E5 servido por{" "}
            <code className="rounded bg-[var(--surface-background)] px-1 font-mono text-xs">
              GET /reports/…/data
            </code>
            . Números agregados seguem as definições canônicas do pipeline (ver glossário
            abaixo).
          </p>
          <button
            type="button"
            className={cn(
              "text-sm font-medium text-[var(--brand-primary)] underline-offset-2 hover:underline",
            )}
            onClick={() => setGlossaryOpen((v) => !v)}
            aria-expanded={glossaryOpen}
          >
            {glossaryOpen ? "Ocultar glossário de fórmulas" : "Ver glossário de fórmulas"}
          </button>
          {glossaryOpen && (
            <ul className="space-y-2 border-l-2 border-[var(--brand-primary)]/40 pl-3">
              {REPORT_FORMULA_CATALOG.map((e) => (
                <li key={e.id}>
                  <span className="font-medium text-[var(--surface-foreground)]">{e.title}</span>
                  {e.codeRef ? (
                    <span className="ml-1 font-mono text-[10px] text-[var(--surface-muted-foreground)]">
                      ({e.codeRef})
                    </span>
                  ) : null}
                  <p className="mt-0.5 text-xs">{e.summary}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </details>
    </section>
  );
}
