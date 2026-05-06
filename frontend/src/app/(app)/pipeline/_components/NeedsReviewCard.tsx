"use client";

import Link from "next/link";
import { AlertTriangle, ArrowRight, X } from "lucide-react";
import { stageName } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export function NeedsReviewCard({
  runId,
  pausedAtStage,
  pendingCount,
  onCancel,
}: {
  runId: string;
  pausedAtStage: string | null;
  pendingCount: number;
  onCancel: () => void;
}) {
  const stageLabel = stageName(pausedAtStage ?? "");

  return (
    <Card id={`pipeline-run-${runId}`} className="mb-8 border-alert/50">
      <CardContent>
        <div className="mb-3 flex items-center gap-3">
          <AlertTriangle aria-hidden className="h-5 w-5 text-alert" />
          <h2 className="font-medium text-alert">
            {pausedAtStage
              ? `Revisão pendente na etapa ${stageLabel}`
              : "Revisão pendente"}
          </h2>
        </div>

        <p className="mb-4 text-sm text-muted-foreground">
          {pendingCount > 0 ? (
            <>
              O processamento parou com{" "}
              <span className="font-medium text-foreground">
                {pendingCount}{" "}
                {pendingCount === 1
                  ? "revisão pendente"
                  : "revisões pendentes"}
              </span>
              . Aprove ou edite cada uma na tela dedicada para retomar o
              pipeline.
            </>
          ) : (
            <>
              O processamento desta etapa exige sua confirmação. Abra a tela de
              revisões para aprovar ou editar os outputs.
            </>
          )}
        </p>

        <div className="flex flex-wrap gap-3">
          <Button
            size="sm"
            nativeButton={false}
            render={<Link href={`/pipeline/runs/${runId}/reviews`} />}
          >
            Revisar agora
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
          <Button size="sm" variant="outline" onClick={onCancel}>
            <X className="mr-2 h-4 w-4" />
            Cancelar execução
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
