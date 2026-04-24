import type { ReactNode } from "react";

export interface ComparisonSide {
  readonly label: string;
  readonly value: ReactNode;
  readonly note?: ReactNode;
}

/** ADR-117 · Fase 3 — comparison block (before/after).
 *
 * Matching `.comparison` + `.comparison-card` EXEMPLO_DE_RELATORIO.html
 * linhas 587-590. Lado esquerdo = contexto negativo (compare-neg bg),
 * direito = positivo (compare-pos bg).
 */
export function ComparisonBlock({
  before,
  after,
  className,
}: {
  readonly before: ComparisonSide;
  readonly after: ComparisonSide;
  readonly className?: string;
}) {
  return (
    <div
      className={className}
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: "var(--space-lg, 16px)",
        margin: "var(--space-md, 12px) 0",
      }}
    >
      <ComparisonCard side={before} bgVar="var(--report-surface-compare-neg)" />
      <ComparisonCard side={after} bgVar="var(--report-surface-compare-pos)" />
    </div>
  );
}

function ComparisonCard({ side, bgVar }: { side: ComparisonSide; bgVar: string }) {
  return (
    <div
      style={{
        background: bgVar,
        borderRadius: "var(--radius-card, 12px)",
        padding: "var(--space-lg, 16px)",
        border: "1px solid var(--surface-border)",
        boxShadow: "var(--shadow-card)",
      }}
    >
      <h4
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "var(--report-font-size-base, 13px)",
          fontWeight: 700,
          marginBottom: "var(--space-sm, 8px)",
          color: "var(--brand-primary)",
        }}
      >
        {side.label}
      </h4>
      <div
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "var(--report-font-size-xl, 22px)",
          fontWeight: 800,
          color: "var(--brand-primary)",
        }}
      >
        {side.value}
      </div>
      {side.note && (
        <p
          style={{
            marginTop: 4,
            fontSize: "var(--report-font-size-sm, 12px)",
            color: "var(--surface-muted-foreground)",
          }}
        >
          {side.note}
        </p>
      )}
    </div>
  );
}
