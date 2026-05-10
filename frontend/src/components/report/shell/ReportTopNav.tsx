"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useReportMode } from "@/components/report/ReportModeProvider";

export interface NavLink {
  readonly id: string;
  readonly label: string;
  readonly num?: string;
  readonly isAppendix?: boolean;
}

export interface NavGroup {
  readonly label?: string;
  readonly links: readonly NavLink[];
}

export type NavDensity = "default" | "compact";

/** Acima desse total de links no modo ativo, faixa entra em modo compacto:
 * apenas o `link.num` aparece; o label só expande no item ativo (scroll-spy).
 * Estratégico tem 16 alvos (com plano_de_acao) → compacta; USA (4) fica normal.
 * ADR-151 (Direção E): Modo Tático removido.
 */
const COMPACT_THRESHOLD = 8;

export interface ReportTopNavProps {
  /** Slot esquerdo — breadcrumb ou brand. Sem fallback. */
  readonly brand?: ReactNode;
  /** Slot direito — ações do relatório (modo, TOC, print, PDF, fonte, tema). */
  readonly actions?: ReactNode;
  readonly groupsByMode: {
    readonly estrategico: readonly NavGroup[];
  };
  /** Container do scroll observado para active link. Default: window. */
  readonly scrollRoot?: HTMLElement | null;
  readonly className?: string;
}

/** ADR-117 · Fase 4 — sticky top-nav do relatório premium.
 *
 * Matching `.nav-sticky` EXEMPLO_DE_RELATORIO.html linhas 178-204 +
 * 1315-1359 (3 grupos por modo). IntersectionObserver atualiza
 * `[data-active]` no link da seção visível.
 */
export function ReportTopNav({
  brand,
  actions,
  groupsByMode,
  scrollRoot,
  className,
}: ReportTopNavProps) {
  const { mode } = useReportMode();
  const [activeId, setActiveId] = useState<string | null>(null);
  const groups = groupsByMode[mode];
  const totalLinks = groups.reduce((acc, g) => acc + g.links.length, 0);
  const density: NavDensity = totalLinks > COMPACT_THRESHOLD ? "compact" : "default";

  useEffect(() => {
    const linkIds = groups.flatMap((g) => g.links.map((l) => l.id));
    const elements = linkIds
      .map((id) => document.getElementById(id))
      .filter((el): el is HTMLElement => el !== null);
    if (elements.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible.length > 0) {
          setActiveId(visible[0].target.id);
        }
      },
      {
        root: scrollRoot ?? null,
        rootMargin: "-120px 0px -50% 0px",
        threshold: [0, 0.25, 0.5, 0.75, 1],
      },
    );
    for (const el of elements) observer.observe(el);
    return () => observer.disconnect();
  }, [groups, scrollRoot, mode]);

  return (
    <nav
      className={className}
      aria-label="Navegação do relatório"
      data-report-topnav
      data-density={density}
      style={{
        position: "sticky",
        top: 0,
        zIndex: 30,
        minHeight: "var(--report-topnav-h, 52px)",
        boxSizing: "border-box",
        background: "var(--report-gradient-nav-sticky)",
        borderBottom: "1px solid rgba(255,255,255,0.08)",
        boxShadow: "0 2px 12px rgba(0,0,0,0.15)",
        display: "flex",
        alignItems: "center",
        padding: "0 20px",
      }}
    >
      {brand && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "10px 16px 10px 0",
            borderRight: "1px solid rgba(255,255,255,0.1)",
            marginRight: 8,
            whiteSpace: "nowrap",
            color: "#fff",
          }}
        >
          {brand}
        </div>
      )}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          flex: 1,
          overflowX: "auto",
          minWidth: 0,
          scrollbarWidth: "none",
        }}
      >
        {groups.map((group, i) => (
          <div
            key={`${mode}-${i}`}
            style={{ display: "flex", alignItems: "center", gap: 2 }}
          >
            {i > 0 && (
              <span
                aria-hidden="true"
                style={{
                  width: 1,
                  height: 20,
                  background: "rgba(255,255,255,0.15)",
                  margin: "0 4px",
                  flexShrink: 0,
                }}
              />
            )}
            {group.label && (
              <span
                style={{
                  fontSize: 9,
                  textTransform: "uppercase",
                  letterSpacing: "0.8px",
                  color: "rgba(255,255,255,0.3)",
                  padding: "0 6px",
                  whiteSpace: "nowrap",
                  fontWeight: 600,
                }}
              >
                {group.label}
              </span>
            )}
            {group.links.map((link) => (
              <NavLinkItem
                key={link.id}
                link={link}
                active={link.id === activeId}
                density={density}
              />
            ))}
          </div>
        ))}
      </div>
      {actions && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginLeft: 12,
            flexShrink: 0,
            paddingLeft: 12,
            borderLeft: "1px solid rgba(255,255,255,0.1)",
          }}
        >
          {actions}
        </div>
      )}
    </nav>
  );
}

function NavLinkItem({
  link,
  active,
  density,
}: {
  link: NavLink;
  active: boolean;
  density: NavDensity;
}) {
  const labelHidden = density === "compact" && !active;
  return (
    <a
      href={`#${link.id}`}
      data-active={active}
      data-density={density}
      aria-current={active ? "location" : undefined}
      aria-label={labelHidden ? link.label : undefined}
      title={labelHidden ? link.label : undefined}
      style={{
        display: "flex",
        alignItems: "center",
        gap: labelHidden ? 0 : 4,
        padding: labelHidden ? "10px 6px" : "10px 10px",
        color: active
          ? "#fff"
          : link.isAppendix
            ? "rgba(255,255,255,0.4)"
            : "rgba(255,255,255,0.7)",
        textDecoration: "none",
        fontSize: 12,
        fontWeight: 500,
        whiteSpace: "nowrap",
        borderRadius: "var(--radius-sm, 4px)",
        background: active ? "rgba(255,255,255,0.12)" : "transparent",
        transition: "all 0.2s",
        fontFamily: "var(--font-body)",
      }}
    >
      {link.num && (
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: 16,
            height: 16,
            borderRadius: "var(--radius-sm, 4px)",
            background: "rgba(255,255,255,0.15)",
            fontSize: 10,
            fontWeight: 700,
            flexShrink: 0,
          }}
        >
          {link.num}
        </span>
      )}
      <span
        style={{
          maxWidth: labelHidden ? 0 : 200,
          opacity: labelHidden ? 0 : 1,
          overflow: "hidden",
          transition: "max-width 0.2s, opacity 0.2s",
        }}
      >
        {link.label}
      </span>
    </a>
  );
}
