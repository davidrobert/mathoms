import type { ReactNode } from "react";

export interface ChangelogEntry {
  readonly id: string;
  readonly headline: ReactNode;
  readonly meta?: ReactNode;
  readonly severity?: "info" | "change" | "highlight";
}

const SEVERITY_BORDER: Record<NonNullable<ChangelogEntry["severity"]>, string> = {
  info: "var(--surface-muted-foreground)",
  change: "var(--brand-info)",
  highlight: "var(--brand-accent)",
};

/** ADR-117 · Fase 3 — changelog list (T0 mudanças do ciclo).
 *
 * Matching `.changelog-list` + `.ciclo-badge` EXEMPLO_DE_RELATORIO.html
 * linhas 869-874.
 */
export function ChangelogList({
  ciclo,
  entries,
  className,
}: {
  readonly ciclo?: string;
  readonly entries: readonly ChangelogEntry[];
  readonly className?: string;
}) {
  return (
    <div className={className}>
      {ciclo && (
        <span
          style={{
            display: "inline-block",
            background: "var(--brand-primary)",
            color: "#fff",
            padding: "4px 12px",
            borderRadius: "var(--radius-sm, 4px)",
            fontSize: 12,
            fontWeight: 600,
            marginBottom: 12,
          }}
        >
          {ciclo}
        </span>
      )}
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {entries.map((entry) => {
          const severity = entry.severity ?? "change";
          return (
            <li
              key={entry.id}
              style={{
                padding: "8px 12px",
                borderLeft: `3px solid ${SEVERITY_BORDER[severity]}`,
                marginBottom: 6,
                background: "var(--surface-background)",
                borderRadius: "0 var(--radius-sm, 4px) var(--radius-sm, 4px) 0",
                fontSize: "var(--report-font-size-md, 14px)",
              }}
            >
              <div>{entry.headline}</div>
              {entry.meta && (
                <div
                  style={{
                    marginTop: 2,
                    fontSize: "var(--report-font-size-xs, 10px)",
                    color: "var(--surface-muted-foreground)",
                  }}
                >
                  {entry.meta}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
