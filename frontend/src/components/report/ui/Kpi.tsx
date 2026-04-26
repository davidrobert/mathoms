import type { ReactNode } from "react";

export type KpiTone = "default" | "green" | "red" | "blue" | "warning";
export type KpiAccent = "default" | "accent" | "danger" | "primary";

const TONE_COLOR: Record<KpiTone, string> = {
  default: "var(--brand-primary)",
  green: "var(--brand-accent)",
  red: "var(--brand-danger)",
  blue: "var(--brand-info)",
  warning: "var(--brand-warning)",
};

const ACCENT_BORDER: Record<KpiAccent, string> = {
  default: "var(--surface-border)",
  accent: "var(--brand-accent)",
  danger: "var(--brand-danger)",
  primary: "var(--brand-primary)",
};

/** ADR-117 · Fase 3 — KPI card base.
 *
 * Matching `.kpi-card` EXEMPLO_DE_RELATORIO.html linhas 256-265.
 * `hero` duplica o peso visual (border-2 + value 32px) por linha 575.
 * `progress` renderiza microbar (linha 581-585).
 */
export interface KpiCardProps {
  readonly label: string;
  readonly value: string;
  readonly sub?: ReactNode;
  readonly tone?: KpiTone;
  readonly accent?: KpiAccent;
  readonly hero?: boolean;
  readonly progress?: { value: number; tone?: "green" | "blue" | "red" };
  readonly className?: string;
}

export function KpiCard({
  label,
  value,
  sub,
  tone = "default",
  accent = "default",
  hero = false,
  progress,
  className,
}: KpiCardProps) {
  return (
    <div
      className={className}
      data-kpi-hero={hero || undefined}
      style={{
        background: "var(--surface-card)",
        borderRadius: "var(--radius-card, 12px)",
        padding: hero ? "24px 20px" : "20px 16px",
        boxShadow: "var(--shadow-card)",
        border: `${hero ? 2 : 1}px solid ${ACCENT_BORDER[accent]}`,
        textAlign: "center",
        position: "relative",
      }}
    >
      <div
        style={{
          fontSize: hero
            ? "var(--report-font-size-base, 13px)"
            : "var(--report-font-size-sm, 12px)",
          color: "var(--surface-muted-foreground)",
          textTransform: "uppercase",
          letterSpacing: "0.5px",
          marginBottom: "var(--space-md, 12px)",
          fontWeight: hero ? 600 : 500,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: "var(--font-display)",
          fontSize: hero ? "32px" : "var(--report-font-size-2xl, 28px)",
          fontWeight: 800,
          color: TONE_COLOR[tone],
          lineHeight: 1.1,
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
      {progress && (
        <div
          style={{
            width: "100%",
            height: 6,
            background: "var(--surface-border)",
            borderRadius: 3,
            marginTop: 8,
            overflow: "hidden",
          }}
          aria-hidden="true"
        >
          <div
            style={{
              width: `${Math.max(0, Math.min(100, progress.value * 100))}%`,
              height: "100%",
              borderRadius: 3,
              background: TONE_COLOR[(progress.tone ?? "green") as KpiTone],
              transition: "width 0.6s ease",
            }}
          />
        </div>
      )}
    </div>
  );
}

/** Grid responsivo de KPI cards. */
export function KpiGrid({
  columns = 4,
  children,
  className,
}: {
  readonly columns?: 3 | 4 | 5 | 6;
  readonly children: ReactNode;
  readonly className?: string;
}) {
  return (
    <div
      className={className}
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(${columns}, 1fr)`,
        gap: "var(--space-lg, 16px)",
        margin: "var(--space-2xl, 24px) 0",
      }}
    >
      {children}
    </div>
  );
}

/** Strip de 5 KPIs para projeção patrimonial (`.proj-kpi-strip`). */
export interface KpiStripItem {
  readonly label: string;
  readonly value: string;
  readonly tone?: "default" | "gap" | "meta" | "year";
  readonly progress?: number;
}

export function KpiStrip({
  items,
  className,
}: {
  readonly items: readonly KpiStripItem[];
  readonly className?: string;
}) {
  return (
    <div
      className={className}
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(${items.length}, 1fr)`,
        gap: 12,
        marginBottom: "var(--space-lg, 16px)",
        padding: "14px 0 10px",
        borderBottom: "1px solid var(--surface-border)",
      }}
    >
      {items.map((item, i) => (
        <div key={i} style={{ textAlign: "center" }}>
          <div
            style={{
              fontSize: 10,
              textTransform: "uppercase",
              letterSpacing: "0.8px",
              color: "var(--surface-muted-foreground)",
              marginBottom: 4,
              fontWeight: 600,
            }}
          >
            {item.label}
          </div>
          <div
            style={{
              fontFamily: "var(--font-display)",
              fontSize:
                item.tone === "year"
                  ? "var(--report-font-size-xl, 22px)"
                  : "var(--report-font-size-lg, 16px)",
              fontWeight: 800,
              color:
                item.tone === "gap"
                  ? "var(--brand-danger)"
                  : item.tone === "meta"
                    ? "var(--brand-info)"
                    : item.tone === "year"
                      ? "var(--brand-accent)"
                      : "var(--brand-primary)",
            }}
          >
            {item.value}
          </div>
          {item.progress !== undefined && (
            <div
              style={{
                marginTop: 6,
                height: 5,
                borderRadius: 3,
                background: "var(--surface-border)",
                overflow: "hidden",
              }}
              aria-hidden="true"
            >
              <div
                style={{
                  width: `${Math.max(0, Math.min(100, item.progress * 100))}%`,
                  height: "100%",
                  borderRadius: 3,
                  background:
                    "linear-gradient(90deg, var(--brand-info), var(--brand-accent))",
                  transition: "width 0.6s ease",
                }}
              />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
