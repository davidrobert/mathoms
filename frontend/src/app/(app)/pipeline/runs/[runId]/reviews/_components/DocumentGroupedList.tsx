"use client";

import { useState } from "react";
import Link from "next/link";

import type { ValidationIssue } from "@/lib/api/pipeline";
import {
  codeSubgroups,
  groupIssuesByDocument,
  type DocumentIssueGroup,
} from "@/lib/review-groups";
import {
  dismissGroup,
  getDismissedGroups,
  restoreDismissedGroups,
} from "@/lib/review-dismissals";
import { getCopy } from "@/lib/validation-copy";

import { ReviewNatureBadge } from "./ReviewNatureBadge";
import {
  CountPill,
  OccurrenceLine,
  SeverityIcon,
} from "./review-card-primitives";

const VISIBLE_PER_CODE = 3;

/**
 * Visão por documento (A32.l6 PR3) — default da tela de review: cascatas do
 * mesmo documento colapsam em 1 card com 1 decisão. Ações MVP (Q3): "Ver
 * documento" + "Dispensar" (client-side; a decisão formal segue sendo
 * aprovar/editar a review inteira).
 */
export function DocumentGroupedList({
  issues,
  reviewId,
  onErrorClick,
}: {
  issues: ValidationIssue[];
  reviewId?: string;
  onErrorClick?: (path: string) => void;
}) {
  const [dismissed, setDismissed] = useState<string[]>(() =>
    getDismissedGroups(reviewId),
  );
  const groups = groupIssuesByDocument(issues);
  const visible = groups.filter((g) => !dismissed.includes(g.key));
  const hiddenCount = groups.length - visible.length;
  const docCount = groups.filter((g) => g.kind !== "truncated").length;
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        {docCount === 1
          ? "1 documento com itens para conferir"
          : `${docCount} documentos com itens para conferir`}
      </p>
      <ul aria-label="Documentos com itens para conferência" className="space-y-3">
        {visible.map((group) => (
          <li key={group.key}>
            <DocumentGroupCard
              group={group}
              defaultOpen={visible.length <= 2}
              onErrorClick={onErrorClick}
              onDismiss={() => setDismissed(dismissGroup(reviewId, group.key))}
            />
          </li>
        ))}
      </ul>
      {hiddenCount > 0 && (
        <button
          type="button"
          className="text-xs text-muted-foreground hover:text-foreground hover:underline"
          onClick={() => setDismissed(restoreDismissedGroups(reviewId))}
        >
          {hiddenCount === 1
            ? "1 item dispensado · restaurar"
            : `${hiddenCount} itens dispensados · restaurar`}
        </button>
      )}
    </div>
  );
}

function DocumentGroupCard({
  group,
  defaultOpen,
  onErrorClick,
  onDismiss,
}: {
  group: DocumentIssueGroup;
  defaultOpen: boolean;
  onErrorClick?: (path: string) => void;
  onDismiss: () => void;
}) {
  const severityLabel = group.severity === "error" ? "erro" : "aviso";
  return (
    <details
      open={defaultOpen}
      className="rounded-lg border border-border bg-card p-3"
    >
      <summary
        className="flex cursor-pointer select-none flex-wrap items-center gap-2 text-sm font-medium text-foreground hover:text-foreground/80"
        aria-label={`${group.label}, ${group.issues.length} itens, ${severityLabel}`}
      >
        <SeverityIcon severity={group.severity} />
        <span className="min-w-0 flex-1 break-words">{group.label}</span>
        <CountPill count={group.issues.length} severity={group.severity} />
      </summary>
      <div className="mt-2 space-y-3 pl-6">
        {codeSubgroups(group).map((sub) => (
          <CodeSubsection key={sub.key} sub={sub} onErrorClick={onErrorClick} />
        ))}
        <GroupActions group={group} onDismiss={onDismiss} />
      </div>
    </details>
  );
}

function CodeSubsection({
  sub,
  onErrorClick,
}: {
  sub: { key: string; issues: ValidationIssue[] };
  onErrorClick?: (path: string) => void;
}) {
  const first = sub.issues[0]!;
  const rest = sub.issues.slice(VISIBLE_PER_CODE);
  return (
    <div className="space-y-1">
      <div className="flex flex-wrap items-center gap-2 text-xs font-medium text-foreground">
        <span>{getCopy(first.code).title}</span>
        {sub.issues.length > 1 && (
          <span className="text-muted-foreground">× {sub.issues.length}</span>
        )}
        <ReviewNatureBadge code={first.code} />
      </div>
      <ul className="space-y-1">
        {sub.issues.slice(0, VISIBLE_PER_CODE).map((issue, idx) => (
          <OccurrenceLine
            key={idx}
            issue={issue}
            onErrorClick={onErrorClick}
            variant="document"
          />
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
                variant="document"
              />
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

function GroupActions({
  group,
  onDismiss,
}: {
  group: DocumentIssueGroup;
  onDismiss: () => void;
}) {
  if (group.kind === "truncated") return null;
  return (
    <div className="flex items-center gap-4 pt-0.5">
      {group.documentId && (
        <Link
          href={`/documents?doc=${group.documentId}`}
          className="text-xs font-medium text-primary hover:underline focus-visible:underline"
        >
          Ver documento
        </Link>
      )}
      <button
        type="button"
        className="text-xs text-muted-foreground hover:text-foreground hover:underline"
        onClick={onDismiss}
      >
        Dispensar
      </button>
    </div>
  );
}
