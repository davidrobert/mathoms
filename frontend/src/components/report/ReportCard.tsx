import { cn } from "@/lib/cn";
import type { CardVariant } from "@/generated/report-layout";
import type { ReactNode } from "react";

interface ReportCardProps {
  variant?: CardVariant;
  size?: "full" | "half";
  title?: string;
  /** Conteúdo renderizado à direita do título (ex: PeriodToggle, badge). */
  headerRight?: ReactNode;
  /** Texto analítico renderizado abaixo do conteúdo do card (padrão chart-conclusion do HTML). */
  conclusion?: string;
  children: ReactNode;
  className?: string;
}

/** F9 · ADR-076 · F1.1 — Card canônico do relatório, com variants do DNA.
 *
 * As classes `.card-variant-*` vêm de `design-tokens/tokens.json` gerado
 * em `frontend/src/styles/tokens.css`. Mudanças de borda/fundo passam por
 * tokens.json — nunca hardcode aqui.
 */
export function ReportCard({
  variant = "feature",
  size = "full",
  title,
  headerRight,
  conclusion,
  children,
  className,
}: ReportCardProps) {
  return (
    <section
      className={cn(
        `card-variant-${variant}`,
        "shadow-[var(--shadow-card)] transition-shadow hover:shadow-[var(--shadow-card-hover)]",
        size === "half" && "md:col-span-1",
        size === "full" && "md:col-span-2",
        className,
      )}
    >
      {(title || headerRight) && (
        <div className="mb-4 flex items-center justify-between gap-2">
          {title && (
            <h3 className="font-display text-lg font-semibold leading-tight">
              {title}
            </h3>
          )}
          {headerRight && <div className="shrink-0">{headerRight}</div>}
        </div>
      )}
      {children}
      {conclusion && (
        <div
          data-chart-conclusion
          className="mt-4 rounded-[var(--radius-md)] border-l-[3px] border-[var(--brand-info)] bg-[color-mix(in_srgb,var(--brand-info)_6%,var(--surface-card))] px-3 py-2.5 text-xs leading-relaxed text-[var(--surface-foreground)]"
        >
          {conclusion}
        </div>
      )}
    </section>
  );
}
