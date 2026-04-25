"use client";

import Link from "next/link";
import { formatDate, formatPeriodRange, formatRelativeTime } from "@/lib/format";

interface ReportSourceStripProps {
  /** Período do cartão do relatório (metadados API). */
  reportPeriod: string | null;
  /** `data_analise` ou `periodo_dados` do JSON de análise, quando existir. */
  analysisPeriod: string | null | undefined;
  /** ISO do `created_at` do relatório — formatamos aqui (relativo + absoluto no tooltip). */
  generatedAtIso: string;
  /** F11.4a — UUID da execução do pipeline (GET report). */
  pipelineRunId?: string | null;
  /** F11.4a — agregado de documentos prontos no workspace. */
  sourceDocumentCount?: number | null;
  /** Documentos efetivamente extraídos pela run que gerou o relatório. */
  consumedDocumentCount?: number | null;
}

/**
 * F11.4 — Faixa discreta de origem dos dados.
 *
 * Linha principal: período + data de geração (info relevante ao usuário).
 * Detalhes técnicos (run ID, contagem de docs) ficam colapsados sob "Auditoria".
 */
function shortRunId(id: string): string {
  const t = id.trim();
  if (t.length <= 12) return t;
  return `${t.slice(0, 8)}…`;
}

export function ReportSourceStrip({
  reportPeriod,
  analysisPeriod,
  generatedAtIso,
  pipelineRunId,
  sourceDocumentCount,
  consumedDocumentCount,
}: ReportSourceStripProps) {
  const rawPeriod =
    (analysisPeriod && String(analysisPeriod).trim()) ||
    reportPeriod ||
    null;
  const periodLabel = formatPeriodRange(rawPeriod);

  const generatedRelative = formatRelativeTime(generatedAtIso);
  const generatedAbsolute = formatDate(generatedAtIso);

  const hasConsumed =
    typeof consumedDocumentCount === "number" && consumedDocumentCount > 0;
  const hasSource = sourceDocumentCount != null && sourceDocumentCount > 0;
  const hasAuditDetails = !!(pipelineRunId || hasConsumed || hasSource);

  return (
    <div
      className="no-print border-b border-[var(--surface-border)] bg-[color-mix(in_srgb,var(--surface-muted)_45%,transparent)] px-4 py-2 text-xs leading-relaxed text-[var(--surface-muted-foreground)]"
      role="note"
      aria-label="Origem dos dados do relatório"
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5">
        <span className="text-[var(--surface-foreground)]">{periodLabel}</span>
        <span className="text-[var(--surface-border)]" aria-hidden>·</span>
        <span title={generatedAbsolute}>gerado {generatedRelative}</span>
        <span className="text-[var(--surface-border)]" aria-hidden>·</span>
        <span>
          dados em{" "}
          <Link
            href="/documents"
            className="text-[var(--brand-primary)] underline-offset-2 hover:underline"
          >
            Documentos
          </Link>
          {" "}e{" "}
          <Link
            href="/pipeline"
            className="text-[var(--brand-primary)] underline-offset-2 hover:underline"
          >
            Pipeline
          </Link>
        </span>

        {hasAuditDetails && (
          <>
            <span className="text-[var(--surface-border)]" aria-hidden>·</span>
            <details className="group inline">
              <summary className="cursor-pointer list-none text-[var(--surface-muted-foreground)] hover:text-[var(--surface-foreground)] select-none">
                Auditoria{" "}
                <span className="inline-block transition-transform group-open:rotate-180" aria-hidden>▾</span>
              </summary>
              <div className="mt-1.5 space-y-1">
                <p>
                  <span className="text-[var(--surface-foreground)]">Gerado em:</span>{" "}
                  <span className="font-mono tabular-nums">{generatedAbsolute}</span>
                </p>
                {pipelineRunId && (
                  <p>
                    <span className="text-[var(--surface-foreground)]">Execução:</span>{" "}
                    <Link
                      href={`/pipeline?run=${encodeURIComponent(pipelineRunId)}`}
                      className="font-mono text-[var(--surface-foreground)] tabular-nums underline-offset-2 hover:underline"
                      title={pipelineRunId}
                    >
                      {shortRunId(pipelineRunId)}
                    </Link>
                  </p>
                )}
                {hasConsumed && (
                  <p>
                    <span className="text-[var(--surface-foreground)]">Analisados:</span>{" "}
                    <span className="font-mono tabular-nums">{consumedDocumentCount}</span> documento(s) extraído(s) pela execução
                  </p>
                )}
                {hasSource && (
                  <p>
                    <span className="text-[var(--surface-foreground)]">No workspace:</span>{" "}
                    <span className="font-mono tabular-nums">{sourceDocumentCount}</span> pronto(s) no momento da consulta
                  </p>
                )}
              </div>
            </details>
          </>
        )}
      </div>
    </div>
  );
}
