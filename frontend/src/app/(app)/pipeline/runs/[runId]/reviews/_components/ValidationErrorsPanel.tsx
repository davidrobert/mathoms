"use client";

import { AlertCircle, AlertTriangle } from "lucide-react";

import { formatCopy, getCopy, summarizeIssues } from "@/lib/validation-copy";
import type { ValidationIssue } from "@/lib/api/pipeline";

import {
  groupIssuesByCode,
  groupLegacyLines,
  type IssueGroup,
  type LegacyGroup,
} from "@/lib/review-groups";

const VISIBLE_OCCURRENCES = 5;

/**
 * Renderiza issues de StageReview agrupadas por tipo (A29.l1 · ADR-308).
 *
 * - `issues` populado (ADR-165/ADR-272): grupos por `code` com copy table.
 * - `issues` null (fallback legacy, runs pré-projeção): grupos por mensagem
 *   normalizada — 18 linhas duplicadas viram 2 grupos com contador.
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
    return <GroupedIssuesList issues={issues} onErrorClick={onErrorClick} />;
  }
  return <GroupedLegacyList errors={errorsLegacy} onErrorClick={onErrorClick} />;
}

function SeverityIcon({ severity }: { severity: "error" | "warning" }) {
  const Icon = severity === "error" ? AlertCircle : AlertTriangle;
  const cls = severity === "error" ? "text-loss" : "text-alert";
  return <Icon aria-hidden className={`h-4 w-4 shrink-0 ${cls}`} />;
}

function CountPill({
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

function GroupSummary({
  title,
  count,
  severity,
}: {
  title: string;
  count: number;
  severity: "error" | "warning";
}) {
  const severityLabel = severity === "error" ? "erro" : "aviso";
  const occurrences = count === 1 ? "1 ocorrência" : `${count} ocorrências`;
  return (
    <summary
      className="flex cursor-pointer select-none items-center gap-2 text-sm font-medium text-foreground hover:text-foreground/80"
      aria-label={`${title}, ${occurrences}, ${severityLabel}`}
    >
      <SeverityIcon severity={severity} />
      <span className="min-w-0 flex-1">{title}</span>
      <CountPill count={count} severity={severity} />
    </summary>
  );
}

function GroupedIssuesList({
  issues,
  onErrorClick,
}: {
  issues: ValidationIssue[];
  onErrorClick?: (path: string) => void;
}) {
  const groups = groupIssuesByCode(issues);
  return (
    <div className="space-y-3">
      {groups.length > 1 && (
        <p className="text-sm text-muted-foreground">{summarizeIssues(issues)}</p>
      )}
      <ul aria-label="Itens agrupados para conferência" className="space-y-3">
        {groups.map((group) => (
          <li key={group.key}>
            <IssueGroupCard
              group={group}
              defaultOpen={groups.length <= 2}
              onErrorClick={onErrorClick}
            />
          </li>
        ))}
      </ul>
    </div>
  );
}

function IssueGroupCard({
  group,
  defaultOpen,
  onErrorClick,
}: {
  group: IssueGroup;
  defaultOpen: boolean;
  onErrorClick?: (path: string) => void;
}) {
  const first = group.issues[0]!;
  const copy = getCopy(first.code);
  const title =
    first.code === "legacy.unmigrated"
      ? firstSentence(first.legacy_message)
      : copy.title;
  return (
    <details
      open={defaultOpen}
      className="rounded-lg border border-border bg-card p-3"
    >
      <GroupSummary
        title={title}
        count={group.issues.length}
        severity={group.severity}
      />
      <div className="mt-2 space-y-2 pl-6">
        <p className="text-xs text-muted-foreground">
          {formatCopy(copy.description, first.context)}
        </p>
        <OccurrenceList group={group} onErrorClick={onErrorClick} />
        {copy.whyItMatters && (
          <details className="text-xs text-muted-foreground">
            <summary className="cursor-pointer font-medium hover:text-foreground">
              Por que isso importa
            </summary>
            <p className="mt-1.5 leading-relaxed">{copy.whyItMatters}</p>
          </details>
        )}
      </div>
    </details>
  );
}

function OccurrenceList({
  group,
  onErrorClick,
}: {
  group: IssueGroup;
  onErrorClick?: (path: string) => void;
}) {
  const visible = group.issues.slice(0, VISIBLE_OCCURRENCES);
  const rest = group.issues.slice(VISIBLE_OCCURRENCES);
  return (
    <div className="space-y-1">
      <ul className="space-y-1">
        {visible.map((issue, idx) => (
          <OccurrenceLine key={idx} issue={issue} onErrorClick={onErrorClick} />
        ))}
      </ul>
      {rest.length > 0 && (
        <details className="text-xs text-muted-foreground">
          <summary className="cursor-pointer hover:text-foreground">
            e mais {rest.length}
          </summary>
          <ul className="mt-1 space-y-1">
            {rest.map((issue, idx) => (
              <OccurrenceLine
                key={idx}
                issue={issue}
                onErrorClick={onErrorClick}
              />
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

function OccurrenceLine({
  issue,
  onErrorClick,
}: {
  issue: ValidationIssue;
  onErrorClick?: (path: string) => void;
}) {
  const label = occurrenceLabel(issue);
  const canNavigate = issue.path !== null && onErrorClick !== undefined;
  return (
    <li className="flex items-baseline gap-2 text-xs text-foreground">
      <span className="min-w-0 flex-1 break-words font-mono">{label}</span>
      {canNavigate && (
        <button
          type="button"
          onClick={() => onErrorClick(issue.path!)}
          className="shrink-0 text-primary hover:underline focus-visible:underline"
        >
          Ir para o campo →
        </button>
      )}
    </li>
  );
}

/** Linha compacta da ocorrência: valor ofensor + referência do documento
 * quando presentes no context; senão a mensagem técnica original. */
function occurrenceLabel(issue: ValidationIssue): string {
  const ctx = issue.context;
  const parts = [ctx["offending_value"], ctx["field"], ctx["artifact_key"]]
    .filter((v) => v !== null && v !== undefined && String(v).length > 0)
    .map(String);
  return parts.length > 0 ? parts.join(" · ") : issue.legacy_message;
}

function firstSentence(message: string): string {
  const cut = message.split(/[;.]/)[0] ?? message;
  return cut.trim();
}

function GroupedLegacyList({
  errors,
  onErrorClick,
}: {
  errors: string | null;
  onErrorClick?: (path: string) => void;
}) {
  const groups = groupLegacyLines(errors);
  if (groups.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Sem pendências registradas.
      </p>
    );
  }
  return (
    <ul aria-label="Itens agrupados para conferência" className="space-y-3">
      {groups.map((group) => (
        <li key={group.key}>
          <LegacyGroupCard
            group={group}
            defaultOpen={groups.length <= 2}
            onErrorClick={onErrorClick}
          />
        </li>
      ))}
    </ul>
  );
}

function LegacyGroupCard({
  group,
  defaultOpen,
  onErrorClick,
}: {
  group: LegacyGroup;
  defaultOpen: boolean;
  onErrorClick?: (path: string) => void;
}) {
  const path = extractPath(group.representative);
  const distinct = [...new Set(group.lines)];
  return (
    <details
      open={defaultOpen}
      className="rounded-lg border border-alert/40 bg-alert/5 p-3"
    >
      <GroupSummary
        title={firstSentence(group.representative)}
        count={group.lines.length}
        severity="warning"
      />
      <div className="mt-2 space-y-1 pl-6 text-xs text-foreground">
        {distinct.length > 1 &&
          distinct.map((line, idx) => (
            <p key={idx} className="break-words font-mono">
              {line}
            </p>
          ))}
        {path !== null && onErrorClick !== undefined && (
          <button
            type="button"
            onClick={() => onErrorClick(path)}
            className="text-primary hover:underline focus-visible:underline"
          >
            Ir para o campo →
          </button>
        )}
      </div>
    </details>
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
