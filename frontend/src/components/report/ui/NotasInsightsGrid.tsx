import type { ReactNode } from "react";

export interface NotasInsightCardProps {
  readonly icon?: ReactNode;
  readonly label: string;
  readonly value: ReactNode;
  readonly sub?: ReactNode;
  readonly tone?: "score" | "cerbasi" | "periodo";
  readonly children?: ReactNode;
}

const TOP_ACCENT: Record<NonNullable<NotasInsightCardProps["tone"]>, string> = {
  score: "var(--brand-primary)",
  cerbasi: "var(--brand-info)",
  periodo: "var(--brand-accent)",
};

/** ADR-117 · Fase 3 — grid de 3 insight-cards.
 *
 * Matching `.notas-insights-grid` + `.notas-insight-card` EXEMPLO_DE_RELATORIO.html
 * linhas 877-903.
 */
export function NotasInsightsGrid({
  children,
  className,
}: {
  readonly children: ReactNode;
  readonly className?: string;
}) {
  return (
    <div
      className={className}
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gap: "var(--space-lg, 16px)",
        marginBottom: "var(--space-xl, 20px)",
      }}
    >
      {children}
    </div>
  );
}

export function NotasInsightCard({
  icon,
  label,
  value,
  sub,
  tone = "score",
  children,
}: NotasInsightCardProps) {
  return (
    <article
      data-notas-tone={tone}
      style={{
        background: "var(--surface-card)",
        borderRadius: "var(--radius-card, 12px)",
        padding: "var(--space-xl, 20px) var(--space-lg, 16px)",
        border: "1px solid var(--surface-border)",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div
        aria-hidden="true"
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 3,
          background: TOP_ACCENT[tone],
        }}
      />
      {icon && (
        <div style={{ fontSize: 20, marginBottom: "var(--space-sm, 8px)" }}>
          {icon}
        </div>
      )}
      <div
        style={{
          fontSize: "var(--report-font-size-xs, 10px)",
          textTransform: "uppercase",
          letterSpacing: "0.6px",
          color: "var(--surface-muted-foreground)",
          fontWeight: 600,
          marginBottom: 4,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "var(--report-font-size-xl, 22px)",
          fontWeight: 700,
          color: "var(--surface-foreground)",
          lineHeight: 1.2,
        }}
      >
        {value}
      </div>
      {sub && (
        <div
          style={{
            fontSize: "var(--report-font-size-sm, 12px)",
            color: "var(--surface-muted-foreground)",
            marginTop: 4,
          }}
        >
          {sub}
        </div>
      )}
      {children}
    </article>
  );
}
