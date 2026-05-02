"use client";

import Link from "next/link";
import { AlertTriangle, CheckCircle2, Pencil } from "lucide-react";

import { stageName } from "@/lib/format";
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
  const Icon =
    review.status === "approved"
      ? CheckCircle2
      : review.status === "edited"
        ? Pencil
        : AlertTriangle;
  const iconClass =
    review.status === "pending" ? "text-alert" : "text-muted-foreground";
  const errorPreview =
    review.validation_errors?.split("\n")[0]?.slice(0, 80) ?? null;

  return (
    <Link
      href={`/pipeline/runs/${runId}/reviews/${review.id}`}
      data-testid={`review-item-${review.id}`}
      className="block rounded-lg border border-border bg-card p-4 transition-colors hover:border-foreground/30 focus-visible:border-ring focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <Icon aria-hidden className={`mt-0.5 h-4 w-4 shrink-0 ${iconClass}`} />
          <div>
            <h3 className="text-sm font-medium text-foreground">
              {stageName(review.stage)}
            </h3>
            <p className="text-xs text-muted-foreground">
              Criado em {formatDate(review.created_at)}
            </p>
            {errorPreview && (
              <p className="mt-2 text-xs text-muted-foreground">{errorPreview}</p>
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
