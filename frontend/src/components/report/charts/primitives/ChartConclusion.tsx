import type { ReactNode } from "react";

/** ADR-117 · Fase 2 — box de conclusão após cada gráfico.
 *
 * Matching `.chart-conclusion` do EXEMPLO_DE_RELATORIO.html (linha 298):
 * border-left accent + background sutil + padding 10px 14px.
 */
export function ChartConclusion({
  children,
  className,
}: {
  readonly children: ReactNode;
  readonly className?: string;
}) {
  return (
    <p
      className={className}
      style={{
        fontSize: "var(--report-font-size-base, 13px)",
        color: "var(--surface-foreground)",
        lineHeight: 1.5,
        margin: "var(--space-xs, 4px) 0 0",
        padding: "10px 14px",
        background: "var(--report-surface-conclusion-bg, var(--surface-muted))",
        borderRadius: "var(--radius-md, 6px)",
        borderLeft: "3px solid var(--brand-info)",
      }}
      data-chart-conclusion
    >
      {children}
    </p>
  );
}
