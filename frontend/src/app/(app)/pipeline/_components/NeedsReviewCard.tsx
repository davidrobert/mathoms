"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";
import { stageName } from "@/lib/format";
import { reviewPauseImpactHint } from "@/lib/pipelineTransparency";
import { isPipelineLlmStage } from "@/lib/pipelineLlmStages";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/Spinner";

export function NeedsReviewCard({
  runId,
  pausedAtStage,
  resuming,
  onResume,
}: {
  runId: string;
  pausedAtStage: string | null;
  resuming: boolean;
  onResume: () => void;
}) {
  return (
    <Card id={`pipeline-run-${runId}`} className="mb-8 border-warning/50">
      <CardContent>
        <div className="flex items-center gap-3 mb-3">
          <AlertTriangle className="h-5 w-5 text-warning" />
          <h2 className="font-medium text-warning">Aguardando sua confirmação</h2>
        </div>
        <p className="text-sm text-muted-foreground mb-2">
          Pausamos o processamento na etapa{" "}
          <span className="font-medium text-foreground">{stageName(pausedAtStage ?? "")}</span>{" "}
          para que você revise antes de continuar.
        </p>
        <p className="text-sm text-muted-foreground mb-3">{reviewPauseImpactHint(pausedAtStage)}</p>
        {pausedAtStage && isPipelineLlmStage(pausedAtStage) && (
          <p className="text-xs text-muted-foreground mb-3 rounded-md border border-border/60 bg-muted/40 px-3 py-2">
            Esta etapa usa leitura assistida por IA. Confira valores e categorias antes de aprovar.
          </p>
        )}
        <div className="flex flex-wrap gap-3">
          <Button size="sm" onClick={onResume} disabled={resuming}>
            {resuming ? (
              <span className="inline-flex items-center gap-2">
                <Spinner size="sm" className="text-primary-foreground" />
                Retomando...
              </span>
            ) : (
              <>
                <RefreshCw className="mr-2 h-4 w-4" />
                Aprovar e Continuar
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
