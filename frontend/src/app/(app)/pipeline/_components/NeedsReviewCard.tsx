"use client";

import { AlertTriangle, RefreshCw, X } from "lucide-react";
import type { StageReviewResponse } from "@/lib/api";
import { stageName } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/Spinner";

/** Quebra `validation_errors` (texto cru do backend) em linhas legíveis.
 * O backend joga errors do validator concatenados por `\n`; alguns stages
 * usam `; ` como separador. Faz split por ambos e remove vazios. */
export function parseValidationErrors(raw: string | null | undefined): string[] {
  if (!raw) return [];
  return raw
    .split(/\n|;\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

export function NeedsReviewCard({
  runId,
  pausedAtStage,
  pendingReviews,
  resuming,
  cancelling,
  onResume,
  onCancel,
}: {
  runId: string;
  pausedAtStage: string | null;
  pendingReviews: StageReviewResponse[];
  resuming: boolean;
  cancelling: boolean;
  onResume: () => void;
  onCancel: () => void;
}) {
  const errors = pendingReviews.flatMap((r) => parseValidationErrors(r.validation_errors));
  const errorCount = errors.length;
  const stageLabel = stageName(pausedAtStage ?? "");
  const detailsOpen = errorCount > 0 && errorCount <= 3;

  return (
    <Card id={`pipeline-run-${runId}`} className="mb-8 border-warning/50">
      <CardContent>
        <div className="flex items-center gap-3 mb-3">
          <AlertTriangle className="h-5 w-5 text-warning" />
          <h2 className="font-medium text-warning">
            {pausedAtStage
              ? `Erros de validação na etapa ${stageLabel}`
              : "Erros de validação no processamento"}
          </h2>
        </div>

        <p className="text-sm text-muted-foreground mb-3">
          {errorCount > 0 ? (
            <>
              O resultado automático teve{" "}
              <span className="font-medium text-foreground">
                {errorCount} {errorCount === 1 ? "erro" : "erros"} de validação
              </span>
              . Você pode aprovar mesmo assim e continuar — o relatório vai usar o
              output como está — ou cancelar e reprocessar.
            </>
          ) : (
            <>
              O processamento desta etapa exige sua confirmação para continuar.
              Aprovar avança com o output como está; cancelar interrompe a execução.
            </>
          )}
        </p>

        {errorCount > 0 && (
          <details
            open={detailsOpen}
            className="mb-4 rounded-md border border-warning/40 bg-warning/5 px-3 py-2"
          >
            <summary className="cursor-pointer text-xs font-medium text-warning">
              {detailsOpen ? "Erros de validação" : `Ver ${errorCount} erros de validação`}
            </summary>
            <ul className="mt-2 list-disc pl-5 font-mono text-xs text-foreground">
              {errors.map((err, idx) => (
                <li key={idx} className="break-words">
                  {err}
                </li>
              ))}
            </ul>
          </details>
        )}

        <p className="text-xs text-muted-foreground mb-3">
          Aprovar não revisa o output: o pipeline avança com os dados que falharam
          a validação. Se o relatório sair errado, reprocesse esta etapa após
          corrigir os documentos de origem.
        </p>

        <div className="flex flex-wrap gap-3">
          <Button size="sm" onClick={onResume} disabled={resuming || cancelling}>
            {resuming ? (
              <span className="inline-flex items-center gap-2">
                <Spinner size="sm" className="text-primary-foreground" />
                Aprovando...
              </span>
            ) : (
              <>
                <RefreshCw className="mr-2 h-4 w-4" />
                Aprovar mesmo assim e continuar
              </>
            )}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={onCancel}
            disabled={resuming || cancelling}
          >
            {cancelling ? (
              <span className="inline-flex items-center gap-2">
                <Spinner size="sm" />
                Cancelando...
              </span>
            ) : (
              <>
                <X className="mr-2 h-4 w-4" />
                Cancelar execução
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
