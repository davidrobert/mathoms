import { cn } from "@/lib/cn";
import type { ReactNode } from "react";

import type { LayoutSectionId } from "@/generated/report-layout";
import { sectionHeading, type ShellSectionId } from "./utils/sectionTitles";

interface ReportSectionProps {
  /** União literal do codegen + seções do shell: id fora das duas fontes não
   *  compila, então o heading nunca cai no fallback que imprimiria o id cru. */
  id: LayoutSectionId | ShellSectionId;
  /** Mode gate — se setado e ≠ do modo ativo, a seção não é renderizada.
   *  Para F1.1 o gate é feito no shell (loop do layout); este prop é
   *  reservado para F3.2. */
  mode?: "estrategico";
  children: ReactNode;
  className?: string;
}

/** F9 · F1.1 — Wrapper de seção do relatório.
 *
 * Renderiza `<section id="...">` com h2 padronizado. O id é consumido pelo
 * TOC via IntersectionObserver (F3.1). A grade de cards fica sob este node
 * em um `<div className="grid md:grid-cols-2 gap-6">`.
 *
 * Não aceita `title`: o heading vem de `sectionHeading(id)`, mesma fonte que
 * o índice consome. A ausência do prop é o gate — enquanto ele existia, 6
 * seções digitavam heading divergente do ToC (A40.l7).
 */
export function ReportSection({
  id,
  children,
  className,
}: ReportSectionProps) {
  const title = sectionHeading(id);
  return (
    <section
      id={id}
      className={cn("scroll-mt-20 mb-12", className)}
      data-report-section
    >
      <header className="mb-6 border-b border-[var(--surface-border)] pb-3">
        <h2 className="font-display text-2xl font-bold text-[var(--surface-foreground)]">
          {title}
        </h2>
      </header>
      {/* `grid-cols-1` explícito, não implícito: sem ele o track é `auto` e cresce
        * até o max-content do filho mais largo, arrastando TODOS os irmãos —
        * inclusive no PDF, onde `md:` nunca casa (a caixa A4 é 703px). Era o que
        * empurrava o SectionSummary 263px para fora da caixa em S3/S4. */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {children}
      </div>
    </section>
  );
}
