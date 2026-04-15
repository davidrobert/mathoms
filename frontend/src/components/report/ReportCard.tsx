import { cn } from "@/lib/utils";
import type { CardVariant } from "@/generated/report-layout";
import type { ReactNode } from "react";

interface ReportCardProps {
  variant?: CardVariant;
  size?: "full" | "half";
  title?: string;
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
      {title && (
        <h3 className="mb-4 font-display text-lg font-semibold leading-tight">
          {title}
        </h3>
      )}
      {children}
    </section>
  );
}
