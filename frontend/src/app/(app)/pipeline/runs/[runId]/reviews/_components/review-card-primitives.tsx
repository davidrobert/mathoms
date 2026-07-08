"use client";

import { AlertCircle, AlertTriangle } from "lucide-react";

import type { ValidationIssue } from "@/lib/api/pipeline";
import { occurrenceIdentityLabel } from "@/lib/review-issue-identity";
import { natureLabelForCode } from "@/lib/review-nature";
import { translateOffendingValue } from "@/lib/review-offending-value";

import { ReviewNatureBadge } from "./ReviewNatureBadge";

/** Primitivas compartilhadas entre a visão por-code (ValidationErrorsPanel)
 * e a visão por-documento (DocumentGroupedList) — A32.l6 PR3. */

export function SeverityIcon({ severity }: { severity: "error" | "warning" }) {
  const Icon = severity === "error" ? AlertCircle : AlertTriangle;
  const cls = severity === "error" ? "text-loss" : "text-alert";
  return <Icon aria-hidden className={`h-4 w-4 shrink-0 ${cls}`} />;
}

export function CountPill({
  count,
  severity,
}: {
  count: number;
  severity: "error" | "warning";
}) {
  const cls =
    severity === "error" ? "bg-loss/10 text-loss" : "bg-alert/10 text-alert";
  return (
    <span
      aria-hidden
      className={`rounded-full px-2 py-0.5 text-[0.65rem] font-medium tabular-nums ${cls}`}
    >
      {count}
    </span>
  );
}

export function GroupSummary({
  title,
  count,
  severity,
  code,
}: {
  title: string;
  count: number;
  severity: "error" | "warning";
  code?: string;
}) {
  const severityLabel = severity === "error" ? "erro" : "aviso";
  const occurrences = count === 1 ? "1 ocorrência" : `${count} ocorrências`;
  const natureLabel = code ? natureLabelForCode(code) : null;
  return (
    <summary
      className="flex cursor-pointer select-none flex-wrap items-center gap-2 text-sm font-medium text-foreground hover:text-foreground/80"
      aria-label={
        `${title}, ${occurrences}, ${severityLabel}` +
        (natureLabel ? `, ${natureLabel}` : "")
      }
    >
      <SeverityIcon severity={severity} />
      <span className="min-w-0 flex-1">{title}</span>
      {code && <ReviewNatureBadge code={code} />}
      <CountPill count={count} severity={severity} />
    </summary>
  );
}

export function firstSentence(message: string): string {
  const cut = message.split(/[;.]/)[0] ?? message;
  return cut.trim();
}

/**
 * Linha de ocorrência. `variant="code"` (default): identidade do documento
 * como texto principal + valor traduzido abaixo. `variant="document"`: a
 * identidade já é o cabeçalho do card — o principal vira o valor traduzido.
 */
export function OccurrenceLine({
  issue,
  onErrorClick,
  variant = "code",
}: {
  issue: ValidationIssue;
  onErrorClick?: (path: string) => void;
  variant?: "code" | "document";
}) {
  const identity = occurrenceIdentityLabel(issue);
  const translated = translateOffendingValue(issue.context["offending_value"]);
  const primary =
    variant === "document" ? (translated ?? firstSentence(issue.legacy_message)) : identity;
  const secondary = variant === "document" ? null : translated;
  const canNavigate = issue.path !== null && onErrorClick !== undefined;
  return (
    <li className="text-xs text-foreground">
      <div className="flex items-baseline gap-2">
        <span className="min-w-0 flex-1 break-words">{primary}</span>
        {canNavigate && (
          <button
            type="button"
            onClick={() => onErrorClick(issue.path!)}
            className="shrink-0 text-primary hover:underline focus-visible:underline"
          >
            Ir para o campo →
          </button>
        )}
      </div>
      {secondary && (
        <p className="mt-0.5 break-words text-muted-foreground">{secondary}</p>
      )}
      <TechnicalDetails issue={issue} />
    </li>
  );
}

/** Dados crus da ocorrência (artifact_key com hash, valor ofensor, esperado) —
 * só aqui, colapsados; nunca no corpo visível do card (A32.l6). */
export function TechnicalDetails({ issue }: { issue: ValidationIssue }) {
  const ctx = issue.context;
  const candidates: Array<[string, unknown]> = [
    ["Referência", ctx["artifact_key"]],
    ["Valor lido", ctx["offending_value"]],
    ["Esperado", ctx["expected"]],
  ];
  const entries = candidates.filter(
    (pair): pair is [string, string] =>
      typeof pair[1] === "string" && pair[1].length > 0,
  );
  if (entries.length === 0) return null;
  return (
    <details className="mt-0.5 text-[0.65rem] text-muted-foreground">
      <summary className="cursor-pointer hover:text-foreground">
        Detalhes técnicos
      </summary>
      <dl className="mt-1 space-y-0.5">
        {entries.map(([term, value]) => (
          <div key={term} className="flex gap-1.5">
            <dt className="shrink-0 font-medium">{term}:</dt>
            <dd className="min-w-0 break-all font-mono">{value}</dd>
          </div>
        ))}
      </dl>
    </details>
  );
}
