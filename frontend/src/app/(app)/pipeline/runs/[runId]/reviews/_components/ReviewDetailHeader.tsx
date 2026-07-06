"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { stageName } from "@/lib/format";
import type { StageReviewResponse } from "@/lib/api";

const STATUS_LABEL: Record<StageReviewResponse["status"], string> = {
  pending: "Pendente",
  approved: "Aprovado",
  edited: "Editado",
};

function headline(status: StageReviewResponse["status"], itemCount: number): string {
  if (status !== "pending") return "Conferência concluída";
  if (itemCount === 0) return "Nada a conferir neste passo";
  const noun = itemCount === 1 ? "1 item" : `${itemCount} itens`;
  return `Conferir ${noun} antes de continuar`;
}

export function ReviewDetailHeader({
  review,
  runId,
  itemCount,
}: {
  review: StageReviewResponse;
  runId: string;
  itemCount: number;
}) {
  return (
    <header className="mb-6">
      <Link
        href={`/pipeline/runs/${runId}/reviews`}
        className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft aria-hidden className="h-3 w-3" /> Voltar para a lista
      </Link>
      <div className="mt-2 flex items-center gap-3">
        <h1 className="font-heading text-xl font-medium text-foreground">
          {headline(review.status, itemCount)}
        </h1>
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
      {review.status === "pending" && itemCount > 0 && (
        <p className="mt-1 text-sm text-muted-foreground">
          Encontramos alguns pontos nos seus documentos que valem uma olhada.
        </p>
      )}
      <details className="mt-1 text-xs text-muted-foreground">
        <summary className="cursor-pointer select-none hover:text-foreground">
          Detalhes técnicos
        </summary>
        <p className="mt-1 pl-1">
          Etapa: {stageName(review.stage)}{" "}
          <span className="font-mono">({review.stage})</span> · Review ID:{" "}
          <span className="font-mono">{review.id}</span>
        </p>
      </details>
    </header>
  );
}
