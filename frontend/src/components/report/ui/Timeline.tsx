import type { ReactNode } from "react";

export type TimelineStatus = "feito" | "pendente" | "aguardando";

export interface TimelineItem {
  readonly id: string;
  readonly date: string;
  readonly action: ReactNode;
  readonly status?: TimelineStatus;
}

const BADGE: Record<TimelineStatus, { bg: string; color: string; label: string }> = {
  feito: { bg: "#DCFCE7", color: "#166534", label: "feito" },
  pendente: { bg: "#FEF3C7", color: "#92400E", label: "pendente" },
  aguardando: { bg: "#DBEAFE", color: "#1E40AF", label: "aguardando" },
};

/** ADR-117 · Fase 3 — timeline (T5 Próximos passos).
 *
 * Matching `.timeline-item` EXEMPLO_DE_RELATORIO.html linhas 836-842.
 */
export function Timeline({
  items,
  className,
}: {
  readonly items: readonly TimelineItem[];
  readonly className?: string;
}) {
  return (
    <ol
      className={className}
      style={{ listStyle: "none", padding: 0, margin: 0 }}
    >
      {items.map((item) => (
        <li
          key={item.id}
          style={{
            display: "flex",
            gap: 12,
            padding: "10px 0",
            borderBottom: "1px solid var(--surface-border)",
          }}
        >
          <time
            dateTime={item.date}
            style={{
              minWidth: 90,
              fontSize: "var(--report-font-size-sm, 12px)",
              fontWeight: 600,
              color: "var(--brand-primary)",
            }}
          >
            {item.date}
          </time>
          <span
            style={{
              flex: 1,
              fontSize: "var(--report-font-size-base, 13px)",
            }}
          >
            {item.action}
          </span>
          {item.status && (
            <span
              data-timeline-status={item.status}
              style={{
                fontSize: "var(--report-font-size-xs, 10px)",
                padding: "2px var(--space-sm, 8px)",
                borderRadius: "var(--radius-sm, 4px)",
                fontWeight: 500,
                background: BADGE[item.status].bg,
                color: BADGE[item.status].color,
                alignSelf: "center",
              }}
            >
              {BADGE[item.status].label}
            </span>
          )}
        </li>
      ))}
    </ol>
  );
}
