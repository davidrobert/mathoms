import type { ReactNode } from "react";

export type BadgeColor = "green" | "red" | "yellow" | "blue" | "neutral";

/** ADR-117 · Fase 3 — badge pill.
 *
 * Matching `.badge-*` de EXEMPLO_DE_RELATORIO.html linhas 442-447.
 */
export function Badge({
  color = "neutral",
  children,
  className,
}: {
  readonly color?: BadgeColor;
  readonly children: ReactNode;
  readonly className?: string;
}) {
  return (
    <span
      className={className}
      data-badge-color={color}
      style={{
        display: "inline-block",
        padding: "2px var(--space-sm, 8px)",
        borderRadius: "var(--report-radius-badge, 10px)",
        fontSize: "var(--report-font-size-sm, 12px)",
        fontWeight: 600,
        background: `var(--report-badge-${color}-bg)`,
        color: `var(--report-badge-${color}-text)`,
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </span>
  );
}
