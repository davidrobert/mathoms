"use client";

import { COLORS, type Pcts } from "./constants";

interface AlocacaoBarProps {
  pcts: Pcts;
  className?: string;
}

export function AlocacaoBar({ pcts, className = "" }: AlocacaoBarProps) {
  return (
    <div
      className={`h-4 w-full overflow-hidden rounded-full bg-muted ${className}`}
    >
      <div className="flex h-full">
        {pcts.renda_fixa_pct > 0 && (
          <div
            className={`${COLORS.renda_fixa} transition-all`}
            style={{ width: `${pcts.renda_fixa_pct}%` }}
          />
        )}
        {pcts.acoes_pct > 0 && (
          <div
            className={`${COLORS.acoes} transition-all`}
            style={{ width: `${pcts.acoes_pct}%` }}
          />
        )}
        {pcts.imoveis_reits_pct > 0 && (
          <div
            className={`${COLORS.imoveis} transition-all`}
            style={{ width: `${pcts.imoveis_reits_pct}%` }}
          />
        )}
        {pcts.liquidez_usd_pct > 0 && (
          <div
            className={`${COLORS.usd} transition-all`}
            style={{ width: `${pcts.liquidez_usd_pct}%` }}
          />
        )}
      </div>
    </div>
  );
}
