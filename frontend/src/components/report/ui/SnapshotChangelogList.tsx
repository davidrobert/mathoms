/**
 * Report Premium UI v2.8 (ADR-148) — render dos `ChangelogEntry[]` do
 * `SnapshotChangelogBuilder`. Lista determinística "Patrimônio cresceu X%
 * desde o relatório anterior". Tokens-only (ADR-076).
 *
 * Distinto de `ChangelogList` (lista genérica de mudanças com `headline`
 * livre + ciclo) — este consome o DTO Pydantic do backend v2.D.1.
 */
export type ChangelogDeltaSignal = "up" | "down" | "stable";

export interface SnapshotChangelogEntryView {
  readonly section_id: string;
  readonly summary: string;
  readonly delta_signal: ChangelogDeltaSignal;
  readonly delta_pct: number | null;
}

const SIGNAL_BORDER: Record<ChangelogDeltaSignal, string> = {
  up: "var(--semantic-success)",
  down: "var(--semantic-danger)",
  stable: "var(--surface-muted-foreground)",
};

export function SnapshotChangelogList({
  entries,
  className,
}: {
  readonly entries: readonly SnapshotChangelogEntryView[];
  readonly className?: string;
}) {
  if (!entries || entries.length === 0) return null;
  return (
    <ul
      className={className}
      data-testid="snapshot-changelog-list"
      style={{ listStyle: "none", padding: 0, margin: "var(--space-md, 12px) 0" }}
    >
      {entries.map((entry) => (
        <li
          key={entry.section_id}
          data-section-id={entry.section_id}
          data-delta-signal={entry.delta_signal}
          style={{
            padding: "8px 12px",
            borderLeft: `3px solid ${SIGNAL_BORDER[entry.delta_signal]}`,
            marginBottom: 6,
            background: "var(--surface-background)",
            borderRadius: "0 var(--radius-sm, 4px) var(--radius-sm, 4px) 0",
            fontSize: "var(--report-font-size-md, 14px)",
            fontFamily: "var(--font-body)",
            color: "var(--brand-primary)",
          }}
        >
          {entry.summary}
        </li>
      ))}
    </ul>
  );
}
