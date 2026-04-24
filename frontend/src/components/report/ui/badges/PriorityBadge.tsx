export type PriorityLevel = "alta" | "media" | "baixa";

const CONFIG: Record<PriorityLevel, { bg: string; label: string }> = {
  alta: { bg: "#DC2626", label: "Alta" },
  media: { bg: "var(--brand-primary)", label: "Média" },
  baixa: { bg: "#6B7280", label: "Baixa" },
};

/** ADR-117 · Fase 3 — priority badge (alta/media/baixa).
 *
 * Matching `.priority-*` EXEMPLO_DE_RELATORIO.html linhas 961-964.
 */
export function PriorityBadge({
  level,
  className,
}: {
  readonly level: PriorityLevel;
  readonly className?: string;
}) {
  const { bg, label } = CONFIG[level];
  return (
    <span
      className={className}
      data-priority={level}
      style={{
        fontSize: "var(--report-font-size-xs, 10px)",
        padding: "2px 8px",
        borderRadius: 4,
        fontWeight: 600,
        display: "inline-block",
        minWidth: 50,
        textAlign: "center",
        background: bg,
        color: "#FFFFFF",
      }}
    >
      {label}
    </span>
  );
}
