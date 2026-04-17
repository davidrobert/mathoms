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
}

/**
 * F11.4 — Faixa discreta de origem dos dados (sem novo endpoint: usa metadados + snapshot).
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
}: ReportSourceStripProps) {
  const period =
    (analysisPeriod && String(analysisPeriod).trim()) ||
    reportPeriod ||
    "—";

  return (
    <div
      className="no-print border-b border-[var(--surface-border)] bg-[color-mix(in_srgb,var(--surface-muted)_45%,transparent)] px-4 py-2.5 text-xs leading-relaxed text-[var(--surface-muted-foreground)]"
      role="note"
      aria-label="Origem dos dados do relatório"
    >
      <p>
        <span className="font-medium text-[var(--surface-foreground)]">
          Origem dos dados:
        </span>{" "}
        consolidados a partir dos documentos deste workspace após o último
        processamento concluído. Gerencie entradas em{" "}
        <Link
          href="/documents"
          className="font-medium text-[var(--brand-primary)] underline-offset-2 hover:underline"
        >
          Documentos
        </Link>{" "}
        e acompanhe execuções em{" "}
        <Link
          href="/pipeline"
          className="font-medium text-[var(--brand-primary)] underline-offset-2 hover:underline"
        >
          Pipeline
        </Link>
        .
      </p>
      {pipelineRunId ? (
        <p className="mt-1.5">
          <span className="font-medium text-[var(--surface-foreground)]">
            Execução do pipeline:
          </span>{" "}
          <Link
            href={`/pipeline?run=${encodeURIComponent(pipelineRunId)}`}
            className="font-mono text-[var(--surface-foreground)] tabular-nums underline-offset-2 hover:underline"
            title={pipelineRunId}
          >
            {shortRunId(pipelineRunId)}
          </Link>
          <span className="text-[var(--surface-muted-foreground)]">
            {" "}
            (detalhes em Pipeline)
          </span>
        </p>
      ) : null}
      <p className="mt-1.5 font-mono tabular-nums">
        Período referenciado: {period}
        <span className="mx-1.5 text-[var(--surface-border)]" aria-hidden>
          ·
        </span>
        Relatório gerado em {generatedAtLabel}
      </p>
    </div>
  );
}
