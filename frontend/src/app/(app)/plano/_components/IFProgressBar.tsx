"use client";

import { Card, CardContent } from "@/components/ui/card";
import { formatCurrency } from "@/lib/format";

interface IFProgressBarProps {
  pct: number;
  faltante: number;
  patrimonio: number;
  metaBrl: number;
}

export function IFProgressBar({
  pct,
  faltante,
  patrimonio,
  metaBrl,
}: IFProgressBarProps) {
  return (
    <Card className="mb-6">
      <CardContent className="py-5">
        <div className="mb-2 flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            Progresso:{" "}
            <span className="font-mono tabular-nums font-medium text-foreground">
              {formatCurrency(patrimonio)}
            </span>{" "}
            de{" "}
            <span className="font-mono tabular-nums font-medium text-foreground">
              {formatCurrency(metaBrl)}
            </span>
          </span>
          <span className="font-mono tabular-nums font-semibold">
            {pct.toFixed(1)}%
          </span>
        </div>
        <div className="h-3 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-gradient-to-r from-brand-500 to-brand-400 transition-all duration-700"
            style={{ width: `${Math.min(pct, 100)}%` }}
          />
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          Faltam{" "}
          <span className="font-mono tabular-nums font-medium">
            {formatCurrency(faltante)}
          </span>{" "}
          para a meta
        </p>
      </CardContent>
    </Card>
  );
}
