import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { formatDelta as fmtDelta } from "@/lib/format";

interface DeltaProps {
  value: number;
  percent?: number;
  currency?: "BRL" | "USD";
  invert?: boolean;
  className?: string;
}

export function Delta({ value, percent, currency, invert = false, className }: DeltaProps) {
  const isPositive = invert ? value <= 0 : value >= 0;
  const isZero = value === 0;
  const formatted = fmtDelta(value, { percent, currency });

  const Icon = isZero ? Minus : isPositive ? TrendingUp : TrendingDown;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 text-sm font-medium font-mono tabular-nums",
        isZero
          ? "text-neutral-financial"
          : isPositive
            ? "text-gain"
            : "text-loss",
        className
      )}
      aria-label={`${isPositive ? "aumento" : "redução"} de ${formatted}`}
    >
      <Icon className="h-3.5 w-3.5 shrink-0" />
      {formatted}
    </span>
  );
}
