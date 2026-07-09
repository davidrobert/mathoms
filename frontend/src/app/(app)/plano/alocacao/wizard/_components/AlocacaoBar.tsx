"use client";

import { CLASS_META, type Pcts } from "./constants";

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
        {CLASS_META.map(({ key, label, color }) =>
          pcts[key] > 0 ? (
            <div
              key={key}
              className="transition-all"
              style={{ width: `${pcts[key]}%`, backgroundColor: color }}
              title={`${label}: ${pcts[key]}%`}
            />
          ) : null,
        )}
      </div>
    </div>
  );
}
