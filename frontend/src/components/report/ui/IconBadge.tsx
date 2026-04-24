import type { ReactNode } from "react";

export type IconBadgeColor = "blue" | "green" | "red" | "orange" | "dark";

const BG: Record<IconBadgeColor, string> = {
  blue: "var(--brand-info)",
  green: "var(--brand-accent)",
  red: "var(--brand-danger)",
  orange: "var(--brand-warning)",
  dark: "var(--brand-primary)",
};

/** ADR-117 · Fase 3 — icon badge (quadrado 24×24 com 1-2 chars).
 *
 * Matching `.icon-badge-*` de EXEMPLO_DE_RELATORIO.html linhas 593-599.
 */
export function IconBadge({
  color = "blue",
  children,
  className,
  ariaLabel,
}: {
  readonly color?: IconBadgeColor;
  readonly children: ReactNode;
  readonly className?: string;
  readonly ariaLabel?: string;
}) {
  return (
    <span
      className={className}
      aria-label={ariaLabel}
      role={ariaLabel ? "img" : undefined}
      aria-hidden={ariaLabel ? undefined : true}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: 24,
        height: 24,
        borderRadius: "var(--radius-md, 6px)",
        fontSize: "var(--report-font-size-sm, 12px)",
        fontWeight: 800,
        color: "#fff",
        background: BG[color],
        verticalAlign: "middle",
      }}
    >
      {children}
    </span>
  );
}
