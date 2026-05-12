"use client";

// A11.W5 · ADR-192 · S9-T05 — apresenta `RiskInferred` do bundle com
// 1-click "Aceitar como risco" (cria `Risk` persistente).
// Idempotência via `useAcceptInferredRisk` (sessionStorage + 409
// gracefully handled).

import { AlertTriangle, Check, ShieldPlus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAcceptInferredRisk } from "@/hooks/useAcceptInferredRisk";
import type { RiskInferred } from "@/lib/api/protections";

interface InferredRisksCardProps {
  workspaceId: string;
  inferred: RiskInferred[];
}

function formatBRLDecimalString(decimal: string | null): string {
  if (!decimal) return "—";
  const n = Number(decimal);
  if (!Number.isFinite(n)) return decimal;
  return n.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
}

export function InferredRisksCard({
  workspaceId,
  inferred,
}: InferredRisksCardProps) {
  const { acceptedKeys, pending, accept } = useAcceptInferredRisk(workspaceId);

  if (inferred.length === 0) {
    return null;
  }

  return (
    <Card data-testid="inferred-risks-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-[var(--semantic-warning)]" />
          Riscos sugeridos pela análise
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="mb-4 text-sm text-muted-foreground">
          Sugestões geradas a partir do baseline patrimonial. Aceite para
          registrar no Plano de Ação.
        </p>
        <ul className="space-y-3">
          {inferred.map((risk) => {
            const isAccepted = acceptedKeys.has(risk.source_calculator);
            const isPending = pending.has(risk.source_calculator);
            return (
              <li
                key={risk.source_calculator}
                className="flex flex-wrap items-start justify-between gap-3 rounded-md border bg-[var(--surface-muted)] p-3"
                data-testid={`inferred-risk-${risk.source_calculator}`}
              >
                <div className="flex-1 min-w-[260px]">
                  <p className="font-medium">{risk.name}</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {risk.rationale}
                  </p>
                  {risk.estimated_impact_brl && (
                    <p className="mt-1 text-xs">
                      <span className="text-muted-foreground">Impacto estimado: </span>
                      <span className="font-mono tabular-nums">
                        {formatBRLDecimalString(risk.estimated_impact_brl)}
                      </span>
                    </p>
                  )}
                </div>
                <Button
                  size="sm"
                  variant={isAccepted ? "outline" : "default"}
                  disabled={isAccepted || isPending}
                  onClick={() => void accept(risk)}
                  data-testid={`accept-risk-${risk.source_calculator}`}
                >
                  {isAccepted ? (
                    <>
                      <Check className="mr-1 h-4 w-4" />
                      Aceito
                    </>
                  ) : isPending ? (
                    "Aceitando..."
                  ) : (
                    <>
                      <ShieldPlus className="mr-1 h-4 w-4" />
                      Aceitar como risco
                    </>
                  )}
                </Button>
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}
