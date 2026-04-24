export type DeadlineStatus = "vencida" | "urgente" | "ok";

const CONFIG: Record<DeadlineStatus, { bg: string; color: string; labelPrefix: string }> = {
  vencida: { bg: "#FEE2E2", color: "#991B1B", labelPrefix: "Vencida" },
  urgente: { bg: "#FEF3C7", color: "#92400E", labelPrefix: "Urgente" },
  ok: { bg: "#F1F5F9", color: "#475569", labelPrefix: "Prazo" },
};

export function deadlineStatus(
  iso: string,
  now: Date = new Date(),
  urgentDays = 7,
): DeadlineStatus {
  const target = new Date(iso);
  if (Number.isNaN(target.getTime())) return "ok";
  const diffMs = target.getTime() - now.getTime();
  if (diffMs < 0) return "vencida";
  if (diffMs < urgentDays * 24 * 60 * 60 * 1000) return "urgente";
  return "ok";
}

function formatBR(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

/** ADR-117 · Fase 3 — badge de prazo, computa status do ISO.
 *
 * Matching `.deadline-*` EXEMPLO_DE_RELATORIO.html linhas 863-866.
 */
export function DeadlineBadge({
  iso,
  now,
  urgentDays = 7,
  className,
}: {
  readonly iso: string;
  readonly now?: Date;
  readonly urgentDays?: number;
  readonly className?: string;
}) {
  const status = deadlineStatus(iso, now, urgentDays);
  const { bg, color, labelPrefix } = CONFIG[status];
  return (
    <span
      className={className}
      data-deadline-status={status}
      style={{
        fontSize: 10,
        padding: "2px 6px",
        borderRadius: 3,
        fontWeight: 600,
        marginLeft: 6,
        whiteSpace: "nowrap",
        background: bg,
        color,
      }}
    >
      {labelPrefix} · {formatBR(iso)}
    </span>
  );
}
