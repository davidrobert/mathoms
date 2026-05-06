"use client";

import Link from "next/link";
import { AlertCircle, AlertTriangle, CheckCircle2, Pencil } from "lucide-react";

import { stageName } from "@/lib/format";
import { summarizeIssues } from "@/lib/validation-copy";
import type { StageReviewResponse } from "@/lib/api";

const STATUS_LABEL: Record<StageReviewResponse["status"], string> = {
  pending: "Pendente",
  approved: "Aprovado",
  edited: "Editado",
};

export function ReviewListItem({
  review,
  runId,
}: {
  review: StageReviewResponse;
  runId: string;
}) {
  const issues = review.validation_issues ?? [];
  const hasError = issues.some((i) => i.severity === "error");
  const errorCount = issues.filter((i) => i.severity === "error").length;
  const warningCount = issues.filter((i) => i.severity === "warning").length;

  const Icon = pickIcon(review.status, hasError);
  const iconClass = pickIconClass(review.status, hasError);

  // Preferimos `summary` derived no backend; fallback para summarizeIssues no
  // frontend (idêntico em runs ≥ onda 2). Para runs pré-cutover (issues=null),
  // cai no truncate legacy de validation_errors.
  const previewText = pickPreviewText(review);

  return (
    <Link
      href={`/pipeline/runs/${runId}/reviews/${review.id}`}
      data-testid={`review-item-${review.id}`}
      className="block rounded-lg border border-border bg-card p-4 transition-colors hover:border-foreground/30 focus-visible:border-ring focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <Icon aria-hidden className={`mt-0.5 h-4 w-4 shrink-0 ${iconClass}`} />
          <div className="min-w-0">
            <h3 className="text-sm font-medium text-foreground">
              {stageName(review.stage)}
            </h3>
            <p className="text-xs text-muted-foreground">
              Criado em {formatDate(review.created_at)}
            </p>
            {previewText && (
              <p
                className="mt-2 line-clamp-2 text-xs text-muted-foreground"
                title={previewText}
              >
                {previewText}
              </p>
            )}
            {(errorCount > 0 || warningCount > 0) && (
              <IssueCounts errors={errorCount} warnings={warningCount} />
            )}
          </div>
        </div>
        <span
          aria-label={`Status: ${STATUS_LABEL[review.status]}`}
          className={`rounded-full px-2 py-0.5 text-[0.7rem] font-medium ${
            review.status === "pending"
              ? "bg-alert/10 text-alert"
              : "bg-muted text-muted-foreground"
          }`}
        >
          {STATUS_LABEL[review.status]}
        </span>
      </div>
    </Link>
  );
}

function pickIcon(status: StageReviewResponse["status"], hasError: boolean) {
  if (status === "approved") return CheckCircle2;
  if (status === "edited") return Pencil;
  return hasError ? AlertCircle : AlertTriangle;
}

function pickIconClass(status: StageReviewResponse["status"], hasError: boolean) {
  if (status !== "pending") return "text-muted-foreground";
  return hasError ? "text-loss" : "text-alert";
}

function pickPreviewText(review: StageReviewResponse): string | null {
  if (review.validation_issues && review.validation_issues.length > 0) {
    return review.summary || summarizeIssues(review.validation_issues);
  }
  if (review.summary) return review.summary;
  return review.validation_errors?.split("\n")[0]?.slice(0, 80) ?? null;
}

function IssueCounts({ errors, warnings }: { errors: number; warnings: number }) {
  return (
    <div className="mt-2 flex flex-wrap items-center gap-1.5">
      {errors > 0 && (
        <span className="rounded-full bg-loss/10 px-2 py-0.5 text-[0.65rem] font-medium text-loss">
          {errors === 1 ? "1 erro" : `${errors} erros`}
        </span>
      )}
      {warnings > 0 && (
        <span className="rounded-full bg-alert/10 px-2 py-0.5 text-[0.65rem] font-medium text-alert">
          {warnings === 1 ? "1 aviso" : `${warnings} avisos`}
        </span>
      )}
    </div>
  );
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
