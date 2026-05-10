"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/cn";

export interface TocLink {
  readonly id: string;
  readonly label: string;
  readonly num?: string;
  readonly isAppendix?: boolean;
}

export interface TocGroup {
  readonly label?: string;
  readonly entries: readonly TocLink[];
}

interface ReportTocProps {
  groups: readonly TocGroup[];
}

/** F9 · F3.1 — Sidebar TOC nativo com scroll-spy, deep-links e capítulos.
 *
 * Diferencia-se da `ReportTopNav` (faixa sticky) carregando:
 *  - headers de capítulo (`group.label`) — "índice tipo livro"
 *  - badge `num` consistente com a faixa
 *  - títulos completos das seções (faixa usa `shortLabel`)
 *
 * Comportamentos:
 *  - inicializa activeId a partir de `window.location.hash` (deep-link)
 *  - IntersectionObserver com debounce para scroll-spy
 *  - hash atualizado em scroll passivo, não só no click
 *  - auto-scroll do TOC para manter o item ativo visível
 */
export function ReportToc({ groups }: ReportTocProps) {
  const flatEntries = useMemo<readonly TocLink[]>(
    () => groups.flatMap((g) => g.entries),
    [groups],
  );

  const [activeId, setActiveId] = useState<string>(() => {
    if (typeof window === "undefined") return "";
    const hash = window.location.hash.replace("#", "");
    return hash || "";
  });
  const navRef = useRef<HTMLElement>(null);
  const isUserClick = useRef(false);

  // Deep-link: scroll to hash on mount
  useEffect(() => {
    if (typeof window === "undefined" || flatEntries.length === 0) return;
    const hash = window.location.hash.replace("#", "");
    if (!hash) return;
    const timer = setTimeout(() => {
      const el = document.getElementById(hash);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
        setActiveId(hash);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [flatEntries]);

  // IntersectionObserver scroll-spy
  useEffect(() => {
    if (flatEntries.length === 0) return;

    let debounceTimer: ReturnType<typeof setTimeout> | null = null;

    const observer = new IntersectionObserver(
      (entries) => {
        if (isUserClick.current) return;

        if (debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
          const visible = entries
            .filter((e) => e.isIntersecting)
            .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
          if (visible[0]) {
            const newId = visible[0].target.id;
            setActiveId(newId);
            if (typeof window !== "undefined") {
              window.history.replaceState(null, "", `#${newId}`);
            }
          }
        }, 80);
      },
      { rootMargin: "-15% 0% -55% 0%", threshold: [0, 0.1, 0.25, 0.5, 0.75, 1] },
    );

    const elements = flatEntries
      .map((entry) => document.getElementById(entry.id))
      .filter((el): el is HTMLElement => el !== null);

    elements.forEach((el) => observer.observe(el));

    return () => {
      observer.disconnect();
      if (debounceTimer) clearTimeout(debounceTimer);
    };
  }, [flatEntries]);

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

  const handleClick = useCallback((id: string) => {
    const el = document.getElementById(id);
    if (!el) return;

    isUserClick.current = true;
    el.scrollIntoView({ behavior: "smooth", block: "start" });
    setActiveId(id);
    if (typeof window !== "undefined") {
      window.history.replaceState(null, "", `#${id}`);
    }

    setTimeout(() => {
      isUserClick.current = false;
    }, 800);
  }, []);

  return (
    <aside className="sidebar-toc no-print hidden w-60 shrink-0 self-start border-r border-[var(--surface-border)] bg-[var(--surface-card)] p-3 lg:sticky lg:top-[var(--report-topnav-h,52px)] lg:block lg:max-h-[calc(100vh-var(--report-topnav-h,52px))] lg:overflow-y-auto">
      <p className="mb-3 px-2 font-display text-xs font-semibold uppercase tracking-wider text-[var(--surface-muted-foreground)]">
        Capítulos
      </p>
      <nav
        ref={navRef}
        className="flex flex-col gap-3"
        aria-label="Índice do relatório"
      >
        {flatEntries.length === 0 && (
          <p className="px-2 py-1.5 text-xs text-[var(--surface-muted-foreground)]">
            Nenhuma seção disponível neste modo.
          </p>
        )}
        {groups.map((group, groupIdx) => (
          <div key={group.label ?? `g${groupIdx}`} className="flex flex-col gap-0.5">
            {group.label && (
              <p className="mb-0.5 px-2 font-display text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--surface-muted-foreground)]/80">
                {group.label}
              </p>
            )}
            {group.entries.map((entry) => (
              <TocButton
                key={entry.id}
                entry={entry}
                active={activeId === entry.id}
                onClick={handleClick}
              />
            ))}
          </div>
        ))}
      </nav>
    </aside>
  );
}

function TocButton({
  entry,
  active,
  onClick,
}: {
  entry: TocLink;
  active: boolean;
  onClick: (id: string) => void;
}) {
  return (
    <button
      data-toc-id={entry.id}
      onClick={() => onClick(entry.id)}
      className={cn(
        "flex items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors",
        active
          ? "bg-[color-mix(in_srgb,var(--brand-primary)_10%,transparent)] font-medium text-[var(--brand-primary)]"
          : entry.isAppendix
            ? "text-[var(--surface-muted-foreground)]/70 hover:bg-[var(--surface-muted)]"
            : "text-[var(--surface-muted-foreground)] hover:bg-[var(--surface-muted)]",
      )}
    >
      {entry.num ? (
        <span
          aria-hidden
          className={cn(
            "inline-flex h-5 min-w-[20px] shrink-0 items-center justify-center rounded text-[10px] font-bold",
            active
              ? "bg-[var(--brand-primary)] text-[var(--brand-primary-foreground,#fff)]"
              : "bg-[var(--surface-muted)] text-[var(--surface-muted-foreground)]",
          )}
        >
          {entry.num}
        </span>
      ) : (
        <ChevronRight
          className={cn(
            "h-3.5 w-3.5 shrink-0 transition-transform",
            active && "rotate-90 text-[var(--brand-primary)]",
          )}
        />
      )}
      <span className="truncate">{entry.label}</span>
    </button>
  );
}
