"use client";

import { cn } from "@/lib/utils";
import { type Period, PERIOD_LABELS } from "@/lib/periodUtils";

const PERIODS: Period[] = ["3m", "6m", "12m", "ytd"];

interface PeriodToggleProps {
  value: Period;
  onChange: (p: Period) => void;
  className?: string;
}

/**
 * Seletor de período de análise (3M / 6M / 12M / YTD).
 * Encaixa no headerRight do ReportCard.
 */
export function PeriodToggle({ value, onChange, className }: PeriodToggleProps) {
  return (
    <div
      role="group"
      aria-label="Período de análise"
      className={cn(
        "flex items-center gap-0.5 rounded-md border border-[var(--surface-border)] p-0.5 text-[11px]",
        className,
      )}
    >
      {PERIODS.map((p) => (
        <button
          key={p}
          type="button"
          aria-pressed={p === value}
          onClick={() => onChange(p)}
          className={cn(
            "rounded-sm px-1.5 py-0.5 font-mono font-semibold tabular-nums transition-colors",
            p === value
              ? "bg-[var(--brand-primary)] text-[var(--brand-primary-foreground)]"
              : "text-[var(--surface-muted-foreground)] hover:bg-[var(--surface-muted)] hover:text-[var(--surface-foreground)]",
          )}
        >
          {PERIOD_LABELS[p]}
        </button>
      ))}
    </div>
  );
}
