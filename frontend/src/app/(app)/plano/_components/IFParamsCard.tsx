"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { IFGoalResponse } from "@/lib/api";
import { formatCurrency } from "@/lib/format";

interface IFParamsCardProps {
  goal: IFGoalResponse;
}

export function IFParamsCard({ goal }: IFParamsCardProps) {
  const i = goal.inputs;
  const d = goal.derived;
  return (
    <Card className="mt-6">
      <CardContent className="py-6">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Parametros atuais
        </h2>
        <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 text-sm md:grid-cols-4">
          <div>
            <dt className="text-muted-foreground">TRS operacional</dt>
            <dd className="mt-1 font-mono tabular-nums">
              {i.trs_pct.toFixed(1)}% a.a.
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Retorno real esperado</dt>
            <dd className="mt-1 font-mono tabular-nums">
              {i.retorno_real_anual_pct.toFixed(1)}% a.a.
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Horizonte</dt>
            <dd className="mt-1 font-mono tabular-nums">
              {i.horizonte_anos} anos
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">
              Meta conservadora (
              {(i.taxa_retirada_conservadora_pct ?? 4.0).toFixed(1)}%)
            </dt>
            <dd className="mt-1 font-mono tabular-nums">
              {formatCurrency(d.if_meta_conservadora_brl)}
            </dd>
          </div>
        </dl>
        <div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
          <Badge variant="outline">Vigente desde</Badge>
          <span>
            {new Date(goal.effective_from).toLocaleDateString("pt-BR")}
          </span>
          {goal.is_template && (
            <Badge variant="secondary">Template — personalize</Badge>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
