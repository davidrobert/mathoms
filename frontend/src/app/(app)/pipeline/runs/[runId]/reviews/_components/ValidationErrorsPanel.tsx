"use client";

import { AlertCircle, AlertTriangle, ChevronDown } from "lucide-react";

import { formatCopy, getCopy } from "@/lib/validation-copy";
import type { ValidationIssue } from "@/lib/api/pipeline";

/**
 * Renderiza issues estruturadas de StageReview (ADR-165 onda 3).
 *
 * - Quando `issues` está populado, renderiza cards estruturados com title +
 *   description + whyItMatters + CTA, usando o copy table de
 *   `validation-copy.ts`.
 * - Quando `issues` é null (runs pré-cutover), faz fallback para a string
 *   legacy `errorsLegacy` quebrada por `\n` (compat com ADR-158).
 */
export function ValidationErrorsPanel({
  issues,
  errorsLegacy,
  onErrorClick,
}: {
  issues: ValidationIssue[] | null;
  errorsLegacy: string | null;
  onErrorClick?: (path: string) => void;
}) {
  if (issues && issues.length > 0) {
    return <StructuredIssuesList issues={issues} onErrorClick={onErrorClick} />;
  }
  return <LegacyErrorsList errors={errorsLegacy} onErrorClick={onErrorClick} />;
}

function StructuredIssuesList({
  issues,
  onErrorClick,
}: {
  issues: ValidationIssue[];
  onErrorClick?: (path: string) => void;
}) {
  // Errors antes de warnings — mantém ordem original dentro de cada grupo.
  const sorted = [...issues].sort((a, b) => {
    if (a.severity === b.severity) return 0;
    return a.severity === "error" ? -1 : 1;
  });
  return (
    <ul aria-label="Issues de validação" className="space-y-3">
      {sorted.map((issue, idx) => (
        <li key={idx}>
          <IssueCard issue={issue} onErrorClick={onErrorClick} />
        </li>
      ))}
    </ul>
  );
}

function IssueCard({
  issue,
  onErrorClick,
}: {
  issue: ValidationIssue;
  onErrorClick?: (path: string) => void;
}) {
  const copy = getCopy(issue.code);
  const Icon = issue.severity === "error" ? AlertCircle : AlertTriangle;
  const iconClass = issue.severity === "error" ? "text-loss" : "text-alert";
  const pillClass =
    issue.severity === "error"
      ? "bg-loss/10 text-loss"
      : "bg-alert/10 text-alert";
  const description = formatCopy(copy.description, issue.context);
  const canNavigate = issue.path !== null && onErrorClick !== undefined;

  return (
    <article
      className="rounded-lg border border-border bg-card p-3"
      aria-labelledby={`issue-${issue.code}-${issue.severity}-title`}
    >
      <div className="flex items-start gap-2">
        <Icon aria-hidden className={`mt-0.5 h-4 w-4 shrink-0 ${iconClass}`} />
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-2">
            <h3
              id={`issue-${issue.code}-${issue.severity}-title`}
              className="text-sm font-medium text-foreground"
            >
              {copy.title}
            </h3>
            <span
              className={`rounded-full px-2 py-0.5 text-[0.65rem] font-medium ${pillClass}`}
            >
              {issue.severity === "error" ? "Erro" : "Aviso"}
            </span>
          </div>
          <p className="mt-1.5 text-xs text-muted-foreground">{description}</p>
          {copy.whyItMatters && (
            <details className="mt-2 text-xs text-muted-foreground">
              <summary className="cursor-pointer font-medium hover:text-foreground">
                Por que isso importa
                <ChevronDown
                  aria-hidden
                  className="ml-1 inline-block h-3 w-3"
                />
              </summary>
              <p className="mt-1.5 leading-relaxed">{copy.whyItMatters}</p>
            </details>
          )}
          {canNavigate && (
            <button
              type="button"
              onClick={() => onErrorClick(issue.path!)}
              className="mt-2 text-xs text-primary hover:underline focus-visible:underline"
            >
              Ir para o campo →
            </button>
          )}
        </div>
      </div>
    </article>
  );
}

function LegacyErrorsList({
  errors,
  onErrorClick,
}: {
  errors: string | null;
  onErrorClick?: (path: string) => void;
}) {
  if (!errors || errors.trim() === "") {
    return (
      <p className="text-sm text-muted-foreground">
        Sem erros de validação registrados.
      </p>
    );
  }
  const lines = errors
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.length > 0);

  return (
    <ul aria-label="Erros de validação" className="space-y-2">
      {lines.map((line, idx) => {
        const path = extractPath(line);
        const clickable = path !== null && onErrorClick !== undefined;
        return (
          <li
            key={idx}
            className="flex items-start gap-2 rounded-md border border-alert/40 bg-alert/5 p-2 text-xs text-foreground"
          >
            <AlertTriangle
              aria-hidden
              className="mt-0.5 h-3.5 w-3.5 shrink-0 text-alert"
            />
            {clickable ? (
              <button
                type="button"
                onClick={() => onErrorClick(path)}
                className="text-left hover:underline focus-visible:underline"
              >
                {line}
              </button>
            ) : (
              <span>{line}</span>
            )}
          </li>
        );
      })}
    </ul>
  );
}

/**
 * Extrai um nome de campo da mensagem de erro legacy (ADR-158, fallback).
 * Tenta:
 * 1. `$.path.field` (jsonpath) → retorna last segment.
 * 2. `field 'name'` ou `field "name"` → retorna `name`.
 * 3. `name:` no começo da linha → retorna `name`.
 *
 * Retorna null se nenhum padrão bate (highlight não funciona — best-effort).
 */
function extractPath(message: string): string | null {
  const jp = /\$\.([\w.[\]]+)/.exec(message);
  if (jp?.[1]) {
    const segs = jp[1].split(".");
    const last = segs[segs.length - 1];
    return last ? last.replace(/\[\d+\]/g, "") : null;
  }
  const quoted = /['"]([\w_]+)['"]/.exec(message);
  if (quoted?.[1]) return quoted[1];
  const prefix = /^([\w_]+):/.exec(message);
  if (prefix?.[1]) return prefix[1];
  return null;
}

/** Helper exportado p/ teste — extrai paths da string legacy `validation_errors`. */
export function extractErrorPaths(errors: string | null): Set<string> {
  if (!errors) return new Set();
  const out = new Set<string>();
  for (const line of errors.split("\n")) {
    const p = extractPath(line.trim());
    if (p) out.add(p);
  }
  return out;
}
