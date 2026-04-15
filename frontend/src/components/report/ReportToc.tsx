"use client";

import { useEffect, useState } from "react";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

export interface TocEntry {
  id: string;
  label: string;
}

interface ReportTocProps {
  sections: TocEntry[];
}

/** F9 · F1.1 — Sidebar TOC nativo.
 *
 * Usa IntersectionObserver observando os `<section data-report-section>`
 * renderizados pelo <ReportSection/>. Clicks fazem scrollIntoView e
 * atualizam via hash (deep-link grátis — impossível no iframe antigo).
 *
 * Refinamentos de scroll-spy ficam em F3.1 (track ativo durante scroll
 * contínuo, highlight no meio da viewport, etc.).
 */
export function ReportToc({ sections }: ReportTocProps) {
  const [activeId, setActiveId] = useState<string>("");

  useEffect(() => {
    if (sections.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible[0]) {
          setActiveId(visible[0].target.id);
        }
      },
      { rootMargin: "-20% 0% -60% 0%", threshold: [0, 0.25, 0.5, 1] },
    );

    const elements = sections
      .map((s) => document.getElementById(s.id))
      .filter((el): el is HTMLElement => el !== null);

    elements.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [sections]);

  const handleClick = (id: string) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "start" });
    // Deep-link via hash para compartilhamento
    if (typeof window !== "undefined") {
      window.history.replaceState(null, "", `#${id}`);
    }
    setActiveId(id);
  };

  return (
    <aside className="sidebar-toc no-print hidden w-60 shrink-0 overflow-y-auto border-r border-[var(--surface-border)] bg-[var(--surface-card)] p-3 lg:block">
      <p className="mb-3 px-2 font-display text-xs font-semibold uppercase tracking-wider text-[var(--surface-muted-foreground)]">
        Índice
      </p>
      <nav className="flex flex-col gap-0.5" aria-label="Índice do relatório">
        {sections.length === 0 && (
          <p className="px-2 py-1.5 text-xs text-[var(--surface-muted-foreground)]">
            Nenhuma seção disponível neste modo.
          </p>
        )}
        {sections.map((section) => (
          <button
            key={section.id}
            onClick={() => handleClick(section.id)}
            className={cn(
              "flex items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm font-body transition-colors",
              activeId === section.id
                ? "bg-[color-mix(in_srgb,var(--brand-primary)_10%,transparent)] font-medium text-[var(--brand-primary)]"
                : "text-[var(--surface-muted-foreground)] hover:bg-[var(--surface-muted)]",
            )}
          >
            <ChevronRight
              className={cn(
                "h-3.5 w-3.5 shrink-0 transition-transform",
                activeId === section.id && "text-[var(--brand-primary)]",
              )}
            />
            <span className="truncate">{section.label}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
}
