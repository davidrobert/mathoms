"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import type { ReportAnalysisData } from "@/lib/api";
import { REPORT_FORMULA_CATALOG } from "@/lib/reportFormulas";
import { cn } from "@/lib/cn";

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
      className="mb-8 rounded-lg border border-[var(--surface-border)] bg-[color-mix(in_srgb,var(--surface-muted)_35%,transparent)]"
      aria-labelledby="report-premissas-heading"
    >
      <details className="group">
        <summary
          className="flex cursor-pointer list-none items-center justify-between gap-2 px-4 py-3 font-medium text-[var(--surface-foreground)] marker:content-none"
          id="report-premissas-heading"
        >
          <span>Premissas e como calculamos</span>
          <ChevronDown className="h-4 w-4 shrink-0 transition group-open:rotate-180" />
        </summary>
        <div className="space-y-3 border-t border-[var(--surface-border)] px-4 py-3 text-sm leading-relaxed text-[var(--surface-muted-foreground)]">
          <p>
            <span className="font-medium text-[var(--surface-foreground)]">Período dos dados:</span>{" "}
            {String(data.periodo_dados ?? "—")}
          </p>
          <p>
            <span className="font-medium text-[var(--surface-foreground)]">Data da análise:</span>{" "}
            {String(data.data_analise ?? "—")}
          </p>
          {premissasSnapshot && (
            <p className="font-mono text-xs tabular-nums opacity-90">
              Snapshot de premissas das metas (referência interna):{" "}
              {JSON.stringify(premissasSnapshot).slice(0, 280)}
              {JSON.stringify(premissasSnapshot).length > 280 ? "…" : ""}
            </p>
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
