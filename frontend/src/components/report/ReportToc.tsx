"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/cn";

export interface TocEntry {
  id: string;
  label: string;
}

interface ReportTocProps {
  sections: TocEntry[];
}

/** F9 · F3.1 — Sidebar TOC nativo com scroll-spy refinado + deep-links.
 *
 * Melhorias sobre F1.1:
 * - Inicializa activeId a partir de `window.location.hash` (deep-link incoming)
 * - Scroll automático na montagem se hash existir (ex: /reports/id#S3)
 * - Debounce do IntersectionObserver para evitar flickering em scroll rápido
 * - Hash atualizado durante scroll passivo (não só no click)
 * - TOC auto-scrolls para manter item ativo visível
 */
export function ReportToc({ sections }: ReportTocProps) {
  const [activeId, setActiveId] = useState<string>(() => {
    if (typeof window === "undefined") return "";
    const hash = window.location.hash.replace("#", "");
    return hash || "";
  });
  const navRef = useRef<HTMLElement>(null);
  const isUserClick = useRef(false);

  // Deep-link: scroll to hash on mount
  useEffect(() => {
    if (typeof window === "undefined" || sections.length === 0) return;
    const hash = window.location.hash.replace("#", "");
    if (!hash) return;
    // Delay to let sections render
    const timer = setTimeout(() => {
      const el = document.getElementById(hash);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
        setActiveId(hash);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [sections]);

  // IntersectionObserver scroll-spy
  useEffect(() => {
    if (sections.length === 0) return;

    let debounceTimer: ReturnType<typeof setTimeout> | null = null;

    const observer = new IntersectionObserver(
      (entries) => {
        // Skip observer during user-click scroll (avoids flickering)
        if (isUserClick.current) return;

        if (debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
          const visible = entries
            .filter((e) => e.isIntersecting)
            .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
          if (visible[0]) {
            const newId = visible[0].target.id;
            setActiveId(newId);
            // Update hash silently during passive scroll
            if (typeof window !== "undefined") {
              window.history.replaceState(null, "", `#${newId}`);
            }
          }
        }, 80);
      },
      { rootMargin: "-15% 0% -55% 0%", threshold: [0, 0.1, 0.25, 0.5, 0.75, 1] },
    );

    const elements = sections
      .map((s) => document.getElementById(s.id))
      .filter((el): el is HTMLElement => el !== null);

    elements.forEach((el) => observer.observe(el));

    return () => {
      observer.disconnect();
      if (debounceTimer) clearTimeout(debounceTimer);
    };
  }, [sections]);

  // Auto-scroll TOC to keep active item visible
  useEffect(() => {
    if (!activeId || !navRef.current) return;
    const activeButton = navRef.current.querySelector(
      `[data-toc-id="${activeId}"]`,
    );
    if (activeButton) {
      activeButton.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [activeId]);

  const handleClick = useCallback(
    (id: string) => {
      const el = document.getElementById(id);
      if (!el) return;

      // Flag to suppress observer during smooth scroll
      isUserClick.current = true;
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      setActiveId(id);
      if (typeof window !== "undefined") {
        window.history.replaceState(null, "", `#${id}`);
      }

      // Re-enable observer after scroll settles
      setTimeout(() => {
        isUserClick.current = false;
      }, 800);
    },
    [],
  );

  return (
    <aside className="sidebar-toc no-print hidden w-60 shrink-0 overflow-y-auto border-r border-[var(--surface-border)] bg-[var(--surface-card)] p-3 lg:block">
      <p className="mb-3 px-2 font-display text-xs font-semibold uppercase tracking-wider text-[var(--surface-muted-foreground)]">
        Índice
      </p>
      <nav
        ref={navRef}
        className="flex flex-col gap-0.5"
        aria-label="Índice do relatório"
      >
        {sections.length === 0 && (
          <p className="px-2 py-1.5 text-xs text-[var(--surface-muted-foreground)]">
            Nenhuma seção disponível neste modo.
          </p>
        )}
        {sections.map((section) => (
          <button
            key={section.id}
            data-toc-id={section.id}
            onClick={() => handleClick(section.id)}
            className={cn(
              "flex items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors",
              activeId === section.id
                ? "bg-[color-mix(in_srgb,var(--brand-primary)_10%,transparent)] font-medium text-[var(--brand-primary)]"
                : "text-[var(--surface-muted-foreground)] hover:bg-[var(--surface-muted)]",
            )}
          >
            <ChevronRight
              className={cn(
                "h-3.5 w-3.5 shrink-0 transition-transform",
                activeId === section.id && "rotate-90 text-[var(--brand-primary)]",
              )}
            />
            <span className="truncate">{section.label}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
}
