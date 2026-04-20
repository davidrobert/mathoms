import { cn } from "@/lib/utils";

interface SectionSummaryProps {
  narrativas: Record<string, unknown> | undefined;
  sectionId: string;
  className?: string;
}

/**
 * Parágrafo editorial de abertura de seção.
 *
 * Lê `narrativas?.[sectionId]` (gerado por E5.N) e renderiza context +
 * conclusion com visual de destaque acima dos cards. Se não houver
 * narrativa para a seção, não renderiza nada.
 *
 * Deve ser filho direto do grid do ReportSection (herda md:col-span-2).
 */
export function SectionSummary({
  narrativas,
  sectionId,
  className,
}: SectionSummaryProps) {
  const entry = narrativas?.[sectionId] as
    | { context?: string; conclusion?: string }
    | undefined;

  const context = entry?.context?.trim();
  const conclusion = entry?.conclusion?.trim();

  if (!context && !conclusion) return null;

  return (
    <div
      className={cn(
        "md:col-span-2 rounded-[var(--radius-card)] border-l-4 border-[var(--brand-primary)]",
        "bg-[color-mix(in_srgb,var(--brand-primary)_4%,var(--surface-card))]",
        "px-5 py-4 shadow-[var(--shadow-card)]",
        className,
      )}
    >
      {context && (
        <p className="text-sm leading-relaxed text-[var(--surface-muted-foreground)]">
          {context}
        </p>
      )}
      {conclusion && (
        <p
          className={cn(
            "text-sm font-medium leading-relaxed text-[var(--surface-foreground)]",
            context && "mt-2",
          )}
        >
          {conclusion}
        </p>
      )}
    </div>
  );
}
