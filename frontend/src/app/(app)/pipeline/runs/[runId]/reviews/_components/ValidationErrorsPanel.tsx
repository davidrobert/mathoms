"use client";

import { useState } from "react";

import { formatCopy, getCopy, summarizeIssues } from "@/lib/validation-copy";
import type { ValidationIssue } from "@/lib/api/pipeline";

import {
  groupIssuesByCode,
  groupLegacyLines,
  type IssueGroup,
  type LegacyGroup,
} from "@/lib/review-groups";
import { issueDocumentId } from "@/lib/review-issue-identity";
import { cn } from "@/lib/cn";

import { DocumentGroupedList } from "./DocumentGroupedList";
import {
  firstSentence,
  GroupSummary,
  OccurrenceLine,
} from "./review-card-primitives";

const VISIBLE_OCCURRENCES = 5;

type ViewMode = "documento" | "tipo";

/**
 * Renderiza issues de StageReview (A29.l1 · ADR-308 · A32.l6).
 *
 * - `issues` com referência a documento: visão por documento é o default
 *   (cascatas do mesmo doc colapsam em 1 card); por tipo vira toggle (PR3).
 * - `issues` sem referência (stages E1/E1.5/E1.6): visão por code direta.
 * - `issues` null (fallback legacy, runs pré-projeção): grupos por mensagem
 *   normalizada — 18 linhas duplicadas viram 2 grupos com contador.
 */
export function ValidationErrorsPanel({
  issues,
  errorsLegacy,
  onErrorClick,
  reviewId,
}: {
  issues: ValidationIssue[] | null;
  errorsLegacy: string | null;
  onErrorClick?: (path: string) => void;
  reviewId?: string;
}) {
  if (issues && issues.length > 0) {
    return (
      <GroupedIssuesViews
        issues={issues}
        reviewId={reviewId}
        onErrorClick={onErrorClick}
      />
    );
  }
  return <GroupedLegacyList errors={errorsLegacy} onErrorClick={onErrorClick} />;
}

function hasDocumentRefs(issues: ValidationIssue[]): boolean {
  return issues.some(
    (i) =>
      issueDocumentId(i) !== null ||
      (typeof i.context["artifact_key"] === "string" &&
        i.context["artifact_key"].length > 0),
  );
}

function GroupedIssuesViews({
  issues,
  reviewId,
  onErrorClick,
}: {
  issues: ValidationIssue[];
  reviewId?: string;
  onErrorClick?: (path: string) => void;
}) {
  const groupable = hasDocumentRefs(issues);
  const [mode, setMode] = useState<ViewMode>("documento");
  if (!groupable) {
    return <GroupedIssuesList issues={issues} onErrorClick={onErrorClick} />;
  }
  return (
    <div className="space-y-3">
      <ViewToggle mode={mode} onChange={setMode} />
      {mode === "documento" ? (
        <DocumentGroupedList
          issues={issues}
          reviewId={reviewId}
          onErrorClick={onErrorClick}
        />
      ) : (
        <GroupedIssuesList issues={issues} onErrorClick={onErrorClick} />
      )}
    </div>
  );
}

function ViewToggle({
  mode,
  onChange,
}: {
  mode: ViewMode;
  onChange: (mode: ViewMode) => void;
}) {
  const options: Array<{ value: ViewMode; label: string }> = [
    { value: "documento", label: "Por documento" },
    { value: "tipo", label: "Por tipo de item" },
  ];
  return (
    <div role="group" aria-label="Modo de agrupamento" className="flex gap-1">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          aria-pressed={mode === opt.value}
          onClick={() => onChange(opt.value)}
          className={cn(
            "rounded-md border px-2 py-1 text-xs font-medium transition-colors",
            mode === opt.value
              ? "border-border bg-secondary text-secondary-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground",
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
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
        code={first.code}
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
