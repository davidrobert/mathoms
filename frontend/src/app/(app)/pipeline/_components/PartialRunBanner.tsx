"use client";

import Link from "next/link";
import { CircleAlert, X } from "lucide-react";
import type { PipelineRunResponse } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { degradedRunCaveat, deriveDegradedStage } from "./degradedStage";

/**
 * Run que entregou relatório com uma etapa final degradada (ADR-357).
 *
 * Mesma gramática visual do `FreeTierSkippedBanner` — "entregou, com lacuna
 * declarada, eis o que fazer" — de propósito: o usuário aprende um padrão só
 * para "faltou o parecer porque é free" e "faltou o parecer porque degradou".
 * Não é o `FailedRunCard` em âmbar: aquele carrega XCircle, headline de erro e
 * "Tentar novamente", e alimentar `lastFailedRun` apagaria o `TriggerCard`.
 */
export function PartialRunBanner({
  run,
  onDismiss,
  onRetryDegraded,
  triggering,
  redirecting,
}: {
  run: PipelineRunResponse;
  onDismiss?: () => void;
  onRetryDegraded?: (fromStage: string) => void;
  triggering?: boolean;
  redirecting?: boolean;
}) {
  const degradedStage = deriveDegradedStage(run);

  return (
    <div
      role="status"
      className="mb-6 flex items-start gap-3 rounded-lg border border-warning/40 bg-warning/10 px-4 py-3 text-sm"
    >
      <CircleAlert className="mt-0.5 h-4 w-4 shrink-0 text-warning" aria-hidden="true" />
      <div className="flex-1 min-w-0">
        <p className="text-foreground">
          <span className="font-medium">{degradedRunCaveat(run)}</span>{" "}
          O restante da análise está completo.
          {redirecting && " Redirecionando..."}
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          {run.report_id && (
            <Link
              href={`/reports/${run.report_id}`}
              className="font-medium text-warning underline underline-offset-2 hover:text-warning/80"
            >
              Ver relatório
            </Link>
          )}
          {/* ADR-357 §8: retomar só a etapa degradada é run novo com
              `from_stage` — não resume. Evita re-pagar o pipeline inteiro. */}
          {onRetryDegraded && degradedStage && (
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs"
              onClick={() => onRetryDegraded(degradedStage)}
              disabled={triggering}
            >
              Tentar a etapa que faltou
            </Button>
          )}
        </div>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          aria-label="Fechar aviso de relatório com ressalva"
          className="text-muted-foreground hover:text-foreground rounded p-0.5 transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
