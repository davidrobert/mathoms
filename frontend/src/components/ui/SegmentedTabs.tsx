import { cn } from "@/lib/cn";

interface TabOption<T extends string> {
  value: T;
  label: string;
}

interface SegmentedTabsProps<T extends string> {
  value: T;
  onChange: (value: T) => void;
  options: ReadonlyArray<TabOption<T>>;
  ariaLabel: string;
  /**
   * "pill": border-based pill buttons (default) — Inbox, Decisões
   * "segment": bg-muted container with active bg-background — Tarefas view toggle
   */
  variant?: "pill" | "segment";
  className?: string;
}

/**
 * Padrão unificado de filter/segmented-tabs em 2 estilos:
 * - "pill": botões com border e arredondamento (filtros de status)
 * - "segment": container bg-muted com tab activo em bg-background (view toggle)
 */
export function SegmentedTabs<T extends string>({
  value,
  onChange,
  options,
  ariaLabel,
  variant = "pill",
  className,
}: SegmentedTabsProps<T>) {
  if (variant === "segment") {
    return (
      <div className={cn("flex gap-1 rounded-lg bg-muted p-1 text-sm", className)}>
        {options.map((opt) => (
          <button
            key={opt.value}
            type="button"
            role="tab"
            aria-selected={value === opt.value}
            onClick={() => onChange(opt.value)}
            className={cn(
              "rounded px-3 py-1 transition",
              value === opt.value
                ? "bg-background font-medium shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {opt.label}
          </button>
        ))}
      </div>
    );
  }

  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className={cn("flex flex-wrap gap-1.5 text-xs", className)}
    >
      {options.map((opt) => {
        const active = value === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(opt.value)}
            className={cn(
              "rounded-full border px-3 py-1 font-medium transition-colors",
              active
                ? "border-foreground bg-foreground text-background"
                : "border-border hover:border-muted-foreground/50",
            )}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
