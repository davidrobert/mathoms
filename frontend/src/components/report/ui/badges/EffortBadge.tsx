export type Effort = "S" | "R" | "O";

const CONFIG: Record<Effort, { bg: string; color: string; label: string }> = {
  S: { bg: "#FEF3C7", color: "#92400E", label: "S · ≤4h" },
  R: { bg: "#DBEAFE", color: "#1E40AF", label: "R · 4-12h" },
  O: { bg: "#F1F5F9", color: "#475569", label: "O · >12h" },
};

/** ADR-117 · Fase 3 — badge de esforço (S/R/O, Short/Regular/Oversize).
 *
 * Matching `.effort-badge-*` EXEMPLO_DE_RELATORIO.html linhas 955-958.
 */
export function EffortBadge({
  effort,
  compact = false,
  className,
}: {
  readonly effort: Effort;
  readonly compact?: boolean;
  readonly className?: string;
}) {
  const { bg, color, label } = CONFIG[effort];
  return (
    <span
      className={className}
      data-effort={effort}
      title={label}
      style={{
        fontSize: "var(--report-font-size-xs, 10px)",
        padding: "1px 5px",
        borderRadius: 3,
        fontWeight: 500,
        background: bg,
        color,
      }}
    >
      {compact ? effort : label}
    </span>
  );
}
