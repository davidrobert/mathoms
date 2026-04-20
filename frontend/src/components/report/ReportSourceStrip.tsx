"use client";

import Link from "next/link";

interface ReportSourceStripProps {
  /** Período do cartão do relatório (metadados API). */
  reportPeriod: string | null;
  /** `data_analise` ou `periodo_dados` do JSON de análise, quando existir. */
  analysisPeriod: string | null | undefined;
  /** Texto já formatado (ex.: `formatDateShort(created_at)`). */
  generatedAtLabel: string;
  /** F11.4a — UUID da execução do pipeline (GET report). */
  pipelineRunId?: string | null;
  /** F11.4a — agregado de documentos prontos no workspace. */
  sourceDocumentCount?: number | null;
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
  generatedAtLabel,
  pipelineRunId,
  sourceDocumentCount,
}: ReportSourceStripProps) {
  const period =
    (analysisPeriod && String(analysisPeriod).trim()) ||
    reportPeriod ||
    "—";

  const hasAuditDetails = !!(pipelineRunId || (sourceDocumentCount != null && sourceDocumentCount > 0));

  return (
    <div
      className="no-print border-b border-[var(--surface-border)] bg-[color-mix(in_srgb,var(--surface-muted)_45%,transparent)] px-4 py-2 text-xs leading-relaxed text-[var(--surface-muted-foreground)]"
      role="note"
      aria-label="Origem dos dados do relatório"
    >
      {/* Linha principal — sempre visível */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 font-mono tabular-nums">
        <span>
          <span className="text-[var(--surface-foreground)]">Período:</span>{" "}
          {period}
        </span>
        <span className="text-[var(--surface-border)]" aria-hidden>·</span>
        <span>
          <span className="text-[var(--surface-foreground)]">Gerado em:</span>{" "}
          {generatedAtLabel}
        </span>
        <span className="text-[var(--surface-border)]" aria-hidden>·</span>
        <span className="font-sans">
          Dados em{" "}
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
              <summary className="cursor-pointer list-none font-sans text-[var(--surface-muted-foreground)] hover:text-[var(--surface-foreground)] select-none">
                Auditoria{" "}
                <span className="inline-block transition-transform group-open:rotate-180" aria-hidden>▾</span>
              </summary>
              <div className="mt-1.5 space-y-1 pl-0 font-sans">
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
                {sourceDocumentCount != null && sourceDocumentCount > 0 && (
                  <p>
                    <span className="text-[var(--surface-foreground)]">Documentos:</span>{" "}
                    <span className="font-mono tabular-nums">{sourceDocumentCount}</span> pronto(s) no workspace
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
