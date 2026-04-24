"use client";

import type { ReactNode } from "react";
import { useId } from "react";

/** ADR-117 · Fase 3 — header de seção colapsível.
 *
 * Matching `.section-header` + `.collapse-icon` EXEMPLO_DE_RELATORIO.html
 * linhas 519-530. Controlled component — caller gerencia estado.
 */
export function CollapsibleSectionHeader({
  title,
  collapsed,
  onToggle,
  hint,
  children,
  className,
}: {
  readonly title: ReactNode;
  readonly collapsed: boolean;
  readonly onToggle: () => void;
  readonly hint?: ReactNode;
  readonly children?: ReactNode;
  readonly className?: string;
}) {
  const panelId = useId();
  return (
    <>
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={!collapsed}
        aria-controls={panelId}
        data-collapsed={collapsed}
        className={className}
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          width: "100%",
          cursor: "pointer",
          userSelect: "none",
          background: "transparent",
          border: 0,
          padding: 0,
          textAlign: "left",
          color: "inherit",
          font: "inherit",
        }}
      >
        <span>{title}</span>
        <span
          aria-hidden="true"
          style={{
            transition: "transform 0.3s ease",
            transform: collapsed ? "rotate(-90deg)" : "rotate(0deg)",
            fontSize: 18,
            color: "var(--surface-muted-foreground)",
            marginLeft: 12,
            flexShrink: 0,
            width: 28,
            height: 28,
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            borderRadius: "50%",
            background: "var(--surface-background)",
            border: "1px solid var(--surface-border)",
          }}
        >
          ▾
        </span>
      </button>
      {collapsed && hint && (
        <div
          style={{
            fontSize: "var(--report-font-size-sm, 12px)",
            color: "var(--surface-muted-foreground)",
            padding: "12px 0",
            fontStyle: "italic",
          }}
        >
          {hint}
        </div>
      )}
      <div
        id={panelId}
        hidden={collapsed}
        style={{
          transition: "max-height 0.5s ease-in-out",
          overflow: "hidden",
        }}
      >
        {children}
      </div>
    </>
  );
}
