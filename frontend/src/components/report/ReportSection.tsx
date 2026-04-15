import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

interface ReportSectionProps {
  id: string;
  title: string;
  /** Mode gate — se setado e ≠ do modo ativo, a seção não é renderizada.
   *  Para F1.1 o gate é feito no shell (loop do layout); este prop é
   *  reservado para F3.2. */
  mode?: "estrategico" | "tatico" | "usa";
  children: ReactNode;
  className?: string;
}

/** F9 · F1.1 — Wrapper de seção do relatório.
 *
 * Renderiza `<section id="...">` com h2 padronizado. O id é consumido pelo
 * TOC via IntersectionObserver (F3.1). A grade de cards fica sob este node
 * em um `<div className="grid md:grid-cols-2 gap-6">`.
 */
export function ReportSection({
  id,
  title,
  children,
  className,
}: ReportSectionProps) {
  return (
    <section
      id={id}
      className={cn("scroll-mt-20 mb-12", className)}
      data-report-section
    >
      <header className="mb-6 border-b border-[var(--surface-border)] pb-3">
        <div className="flex items-baseline gap-3">
          <span className="font-mono text-sm font-medium text-[var(--brand-primary)]">
            {id}
          </span>
          <h2 className="font-display text-2xl font-bold text-[var(--surface-foreground)]">
            {title}
          </h2>
        </div>
      </header>
      <div className="grid gap-6 md:grid-cols-2">{children}</div>
    </section>
  );
}
