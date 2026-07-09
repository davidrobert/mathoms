"use client";

import { CheckCircle2 } from "lucide-react";

/**
 * Barra de progresso Σ→100 (ADR-141 emenda item 11).
 * `warning` durante edição · `danger` ao tentar avançar com Σ≠100 · `ok` em 100%.
 */
export type AlocacaoProgressState = "ok" | "warning" | "danger";

const STATE_COLOR: Record<AlocacaoProgressState, string> = {
  ok: "var(--semantic-success)",
  warning: "var(--semantic-warning)",
  danger: "var(--semantic-danger)",
};

interface AlocacaoProgressProps {
  soma: number;
  state: AlocacaoProgressState;
  className?: string;
}

export function AlocacaoProgress({
  soma,
  state,
  className = "",
}: AlocacaoProgressProps) {
  const color = STATE_COLOR[state];
  const width = Math.min(Math.max(soma, 0), 100);

  return (
    <div
      className={className}
      data-testid="alocacao-progress"
      data-state={state}
    >
      <div className="flex items-center justify-between text-sm">
        <span className="flex items-center gap-1.5 text-muted-foreground">
          {state === "ok" && (
            <CheckCircle2
              className="h-4 w-4"
              style={{ color }}
              aria-hidden="true"
            />
          )}
          Total alocado
        </span>
        <span className="font-mono tabular-nums font-medium" style={{ color }}>
          {soma}% / 100%
        </span>
      </div>

      <div
        className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-muted"
        role="progressbar"
        aria-valuenow={soma}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Soma dos percentuais de alocação"
      >
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${width}%`, backgroundColor: color }}
        />
      </div>

      {state !== "ok" && (
        <p className="mt-1.5 text-xs" style={{ color }}>
          {soma > 100
            ? `Passou ${soma - 100}% — reduza para fechar em 100%.`
            : `Faltam ${100 - soma}% para fechar em 100%.`}
        </p>
      )}
    </div>
  );
}
