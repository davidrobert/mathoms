import type { ReactNode } from "react";

export interface CoverMeta {
  readonly label: string;
  readonly value: ReactNode;
}

export interface ReportCoverProps {
  readonly badge?: string;
  readonly title: string;
  readonly subtitle?: string;
  readonly meta?: readonly CoverMeta[];
  readonly className?: string;
}

/** ADR-117 · Fase 4 — cover hero do relatório premium.
 *
 * Matching `.cover-hero` EXEMPLO_DE_RELATORIO.html linhas 152-177:
 * - Gradient azul profundo com 2 blobs radiais decorativos
 * - Badge caps-lock com letter-spacing
 * - Título Plus Jakarta Sans 800 + subtítulo com gradient-clip
 * - Divider 64px + meta grid (4 cards translúcidos)
 */
export function ReportCover({
  badge,
  title,
  subtitle,
  meta = [],
  className,
}: ReportCoverProps) {
  return (
    <header
      className={className}
      data-report-cover
      style={{
        position: "relative",
        overflow: "hidden",
        padding: "60px 40px",
        color: "#fff",
        background: "var(--report-gradient-cover-primary)",
      }}
    >
      <span
        aria-hidden="true"
        style={{
          position: "absolute",
          top: "-50%",
          right: "-20%",
          width: 600,
          height: 600,
          background:
            "radial-gradient(circle, rgba(46,134,171,0.15) 0%, transparent 70%)",
          pointerEvents: "none",
        }}
      />
      <span
        aria-hidden="true"
        style={{
          position: "absolute",
          bottom: "-30%",
          left: "-10%",
          width: 400,
          height: 400,
          background:
            "radial-gradient(circle, rgba(45,198,83,0.1) 0%, transparent 70%)",
          pointerEvents: "none",
        }}
      />
      <div style={{ position: "relative", maxWidth: 1120, margin: "0 auto" }}>
        {badge && (
          <span
            style={{
              display: "inline-block",
              border: "1px solid rgba(255,255,255,0.2)",
              borderRadius: "var(--radius-pill, 9999px)",
              padding: "4px 16px",
              fontSize: "var(--report-font-size-sm, 12px)",
              letterSpacing: 2,
              textTransform: "uppercase",
              marginBottom: 24,
              color: "rgba(255,255,255,0.7)",
              fontFamily: "var(--font-body)",
            }}
          >
            {badge}
          </span>
        )}
        <h1
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "var(--report-font-size-3xl, 38px)",
            fontWeight: 800,
            lineHeight: 1.1,
            margin: 0,
            marginBottom: 4,
          }}
        >
          {title}
        </h1>
        {subtitle && (
          <p
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "var(--report-font-size-xl, 22px)",
              fontWeight: 600,
              background: "var(--report-gradient-cover-subtitle)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
              color: "transparent",
              marginTop: 0,
              marginBottom: 16,
            }}
          >
            {subtitle}
          </p>
        )}
        <span
          aria-hidden="true"
          style={{
            display: "block",
            width: 64,
            height: 3,
            background: "var(--report-gradient-cover-divider)",
            margin: "16px 0 24px",
            borderRadius: 2,
          }}
        />
        {meta.length > 0 && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: `repeat(${Math.min(meta.length, 4)}, 1fr)`,
              gap: 16,
            }}
          >
            {meta.map((m, i) => (
              <div
                key={i}
                style={{
                  background: "rgba(255,255,255,0.06)",
                  borderRadius: "var(--radius-lg, 8px)",
                  padding: "12px 16px",
                }}
              >
                <div
                  style={{
                    fontSize: "var(--report-font-size-sm, 12px)",
                    color: "rgba(255,255,255,0.7)",
                    textTransform: "uppercase",
                    letterSpacing: 1,
                  }}
                >
                  {m.label}
                </div>
                <div
                  style={{
                    fontSize: "var(--report-font-size-md, 14px)",
                    fontWeight: 600,
                    marginTop: 2,
                  }}
                >
                  {m.value}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </header>
  );
}
