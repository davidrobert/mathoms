"use client";

import { useState } from "react";
import { Check, Pencil, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/Spinner";
import { cn } from "@/lib/cn";
import type { StageReviewActionRequest, StageReviewResponse } from "@/lib/api";

import { JsonEditor } from "./JsonEditor";

type Mode = "idle" | "editing";

export function ReviewActions({
  review,
  submitting,
  onSubmit,
  className,
  errorCount = 0,
}: {
  review: StageReviewResponse;
  submitting: boolean;
  onSubmit: (req: StageReviewActionRequest) => Promise<void>;
  className?: string;
  errorCount?: number;
}) {
  const [mode, setMode] = useState<Mode>("idle");
  const [edited, setEdited] = useState<Record<string, unknown> | null>(null);

  const isPending = review.status === "pending";

  if (!isPending) {
    return (
      <p className="rounded-lg border border-border bg-muted/40 p-3 text-sm text-muted-foreground">
        Esta revisão já foi processada (status: {review.status}). Nenhuma ação
        adicional disponível.
      </p>
    );
  }

  async function handleApprove() {
    await onSubmit({ action: "approve" });
  }

  async function handleEdit() {
    if (!edited) return;
    await onSubmit({ action: "edit", edited_output_json: edited });
  }

  const approveAriaLabel =
    errorCount > 0
      ? `Aprovar como está, ${errorCount} ${
          errorCount === 1 ? "erro pendente" : "erros pendentes"
        }`
      : undefined;

  return (
    <section
      aria-label="Ações da revisão"
      className={cn("space-y-4", mode === "idle" ? className : undefined)}
    >
      {mode === "idle" && (
        <div className="flex flex-wrap gap-2">
          <Button
            onClick={handleApprove}
            disabled={submitting}
            aria-label={approveAriaLabel}
          >
            {submitting ? (
              <span className="inline-flex items-center gap-2">
                <Spinner size="sm" className="text-primary-foreground" />
                Aprovando…
              </span>
            ) : (
              <>
                <Check className="mr-2 h-4 w-4" />
                Aprovar como está
              </>
            )}
          </Button>
          <Button
            variant="outline"
            onClick={() => setMode("editing")}
            disabled={submitting}
          >
            <Pencil className="mr-2 h-4 w-4" />
            Editar e aprovar
          </Button>
        </div>
      )}

      {mode === "editing" && (
        <div className="space-y-3">
          <JsonEditor
            initialValue={review.original_output_json}
            onValidChange={setEdited}
          />
          <div className="flex flex-wrap gap-2">
            <Button onClick={handleEdit} disabled={submitting || edited === null}>
              {submitting ? (
                <span className="inline-flex items-center gap-2">
                  <Spinner size="sm" className="text-primary-foreground" />
                  Salvando…
                </span>
              ) : (
                <>
                  <Check className="mr-2 h-4 w-4" />
                  Salvar edição e aprovar
                </>
              )}
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                setMode("idle");
                setEdited(null);
              }}
              disabled={submitting}
            >
              <X className="mr-2 h-4 w-4" />
              Cancelar edição
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}
