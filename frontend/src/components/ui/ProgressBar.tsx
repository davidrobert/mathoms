import { cn } from "@/lib/cn";

interface ProgressBarProps {
  value: number;
  min?: number;
  max?: number;
  /** Descrição para leitores de tela — obrigatório (WCAG 4.1.2). */
  ariaLabel: string;
  /** Estilo do trilho (fundo). */
  className?: string;
  /** Estilo do preenchimento. */
  barClassName?: string;
}

export function ProgressBar({
  value,
  min = 0,
  max = 100,
  ariaLabel,
  className,
  barClassName,
}: ProgressBarProps) {
  const clamped = Math.min(Math.max(value, min), max);
  const pct = max > min ? ((clamped - min) / (max - min)) * 100 : 0;
  return (
    <div
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={min}
      aria-valuemax={max}
      aria-label={ariaLabel}
      className={cn(
        "h-2 w-full overflow-hidden rounded-full bg-[var(--surface-muted)]",
        className
      )}
    >
      <div
        className={cn(
          "h-full rounded-full bg-[var(--brand-primary)] transition-[width]",
          barClassName
        )}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}
