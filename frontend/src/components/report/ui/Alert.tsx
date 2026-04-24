import type { ReactNode } from "react";

export type AlertSeverity = "info" | "success" | "warning" | "danger";

const BORDER_COLOR: Record<AlertSeverity, string> = {
  info: "var(--brand-info)",
  success: "var(--brand-accent)",
  warning: "var(--brand-warning)",
  danger: "var(--brand-danger)",
};

/** ADR-117 · Fase 3 — alert box.
 *
 * Matching `.alert-*` de EXEMPLO_DE_RELATORIO.html linhas 432-436.
 * Background + text puxam de `--report-alert-*` (token).
 */
export function Alert({
  severity = "info",
  icon,
  children,
  className,
}: {
  readonly severity?: AlertSeverity;
  readonly icon?: ReactNode;
  readonly children: ReactNode;
  readonly className?: string;
}) {
  return (
    <div
      role={severity === "danger" ? "alert" : "status"}
      aria-live={severity === "danger" ? "assertive" : "polite"}
      className={className}
      data-alert-severity={severity}
      style={{
        padding: "14px 18px",
        borderRadius: "var(--radius-lg, 8px)",
        fontSize: "var(--report-font-size-base, 13px)",
        background: `var(--report-alert-${severity}-bg)`,
        color: `var(--report-alert-${severity}-text)`,
        borderLeft: `4px solid ${BORDER_COLOR[severity]}`,
        display: "flex",
        gap: 12,
        alignItems: "flex-start",
      }}
    >
      {icon && <span aria-hidden="true" style={{ flexShrink: 0, marginTop: 2 }}>{icon}</span>}
      <div style={{ flex: 1 }}>{children}</div>
    </div>
  );
}
