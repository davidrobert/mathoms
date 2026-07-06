"use client";

import { useState } from "react";
import { Check, Pencil, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/Spinner";
import { useConfirmDialog } from "@/components/ConfirmDialog";
import { cn } from "@/lib/cn";
import type { StageReviewActionRequest, StageReviewResponse } from "@/lib/api";

import { JsonEditor } from "./JsonEditor";

type Mode = "idle" | "editing";

/** Stages de ingestão: aprovar com erros = documentos ficam de fora do
 * relatório (skipped_inputs). Nos demais (LLM), os dados entram como estão. */
function isIngestionStage(stage: string): boolean {
  return stage === "reconcile_transactions" || stage === "E3";
}

function proceedLabel(errorCount: number, ingestion: boolean): string {
  if (errorCount === 0) return "Continuar assim mesmo";
  if (!ingestion) {
    return errorCount === 1
      ? "Continuar sem corrigir (1 pendência)"
      : `Continuar sem corrigir (${errorCount} pendências)`;
  }
  return errorCount === 1
    ? "Continuar sem este documento"
    : `Continuar sem estes ${errorCount} documentos`;
}

function consequenceText(
  errorCount: number,
  warningCount: number,
  ingestion: boolean,
): string {
  if (errorCount > 0 && ingestion) {
    const n = errorCount === 1 ? "Este documento fica" : `Estes ${errorCount} documentos ficam`;
    return `${n} de fora do relatório. Você pode enviá-los corrigidos depois.`;
  }
  if (errorCount > 0) {
    return "A análise continua com os dados como estão — as pendências acima não serão corrigidas. Você pode corrigir e reprocessar depois.";
  }
  if (warningCount > 0) {
    const n = warningCount === 1 ? "Este item entra" : `Estes ${warningCount} itens entram`;
    return `${n} no relatório como estão. Se algum estiver errado, os números podem sair distorcidos.`;
  }
  return "Nada a corrigir — a análise continua de onde parou.";
}

export function ReviewActions({
  review,
  submitting,
  onSubmit,
  className,
  errorCount = 0,
  warningCount = 0,
}: {
  review: StageReviewResponse;
  submitting: boolean;
  onSubmit: (req: StageReviewActionRequest) => Promise<void>;
  className?: string;
  errorCount?: number;
  warningCount?: number;
}) {
  const [mode, setMode] = useState<Mode>("idle");
  const [edited, setEdited] = useState<Record<string, unknown> | null>(null);
  const { confirm, dialog } = useConfirmDialog();

  const isPending = review.status === "pending";
  const ingestion = isIngestionStage(review.stage);
  const hasItems = errorCount + warningCount > 0;

  if (!isPending) {
    return (
      <p className="rounded-lg border border-border bg-muted/40 p-3 text-sm text-muted-foreground">
        Esta conferência já foi concluída. Nenhuma ação adicional disponível.
      </p>
    );
  }

  async function handleApprove() {
    if (errorCount > 0) {
      const ok = await confirm({
        title:
          errorCount === 1
            ? "Continuar sem 1 documento?"
            : `Continuar sem ${errorCount} ${ingestion ? "documentos" : "pendências"}?`,
        description: ingestion
          ? "O relatório será gerado sem os dados destes documentos. Nada é apagado — eles continuam na sua lista para revisar quando quiser."
          : "A análise continua com os dados como estão. Você pode corrigir os documentos e reprocessar depois.",
        confirmLabel: "Continuar assim",
      });
      if (!ok) return;
    }
    await onSubmit({ action: "approve" });
  }

  async function handleEdit() {
    if (!edited) return;
    await onSubmit({ action: "edit", edited_output_json: edited });
  }

  return (
    <section
      aria-label="Ações da conferência"
      className={cn("space-y-4", mode === "idle" ? className : undefined)}
    >
      {dialog}
      {mode === "idle" && (
        <div className="space-y-2">
          <div className="flex flex-wrap gap-2">
            {hasItems ? (
              <>
                <Button onClick={() => setMode("editing")} disabled={submitting}>
                  <Pencil className="mr-2 h-4 w-4" />
                  Editar e continuar
                </Button>
                <Button
                  variant="outline"
                  onClick={handleApprove}
                  disabled={submitting}
                  aria-describedby="review-approve-consequence"
                >
                  {submitting ? (
                    <span className="inline-flex items-center gap-2">
                      <Spinner size="sm" />
                      Continuando…
                    </span>
                  ) : (
                    proceedLabel(errorCount, ingestion)
                  )}
                </Button>
              </>
            ) : (
              <>
                <Button
                  onClick={handleApprove}
                  disabled={submitting}
                  aria-describedby="review-approve-consequence"
                >
                  {submitting ? (
                    <span className="inline-flex items-center gap-2">
                      <Spinner size="sm" className="text-primary-foreground" />
                      Continuando…
                    </span>
                  ) : (
                    <>
                      <Check className="mr-2 h-4 w-4" />
                      Aprovar e continuar
                    </>
                  )}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setMode("editing")}
                  disabled={submitting}
                >
                  <Pencil className="mr-2 h-4 w-4" />
                  Editar antes
                </Button>
              </>
            )}
          </div>
          <p
            id="review-approve-consequence"
            className="text-xs text-muted-foreground"
          >
            {consequenceText(errorCount, warningCount, ingestion)}
          </p>
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
                  Salvar e continuar
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
