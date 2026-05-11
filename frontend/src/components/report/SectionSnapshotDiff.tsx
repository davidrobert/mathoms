/**
 * Report Premium UI v2.8 (ADR-148) — wrapper que filtra `comparisons` +
 * `changelog` do payload E5 por `sectionId` e delega ao primitivo.
 *
 * Render condicional: payload `null` (primeiro relatório) OU seção sem
 * delta acima do threshold (todos os items `stable`) ⇒ renderiza nada.
 *
 * Filtragem `stable` (2026-05-11, pós-revisão product-designer): linha
 * com Δ ≈ 0% num card de "o que mudou" é signal/noise péssimo. O builder
 * já filtra `entries`; aqui filtramos `items` na mesma régua antes de
 * passar ao primitivo. Plano canônico para redesign profundo:
 * `docs/plan/SNAPSHOT_CHANGELOG_V3/_README.md`.
 */
import type {
  ChangelogEntryRead,
  ComparisonItemRead,
  ReportAnalysisData,
} from "@/lib/api";
import {
  ComparisonItemsBlock,
  type ComparisonItemView,
} from "./ui/ComparisonItemsBlock";
import {
  SnapshotChangelogList,
  type SnapshotChangelogEntryView,
} from "./ui/SnapshotChangelogList";

function toItemView(item: ComparisonItemRead): ComparisonItemView {
  return {
    section_id: item.section_id,
    section_label: item.section_label,
    before: item.before,
    after: item.after,
    delta_pct: item.delta_pct,
    delta_signal: item.delta_signal,
  };
}

function toEntryView(entry: ChangelogEntryRead): SnapshotChangelogEntryView {
  return {
    section_id: entry.section_id,
    summary: entry.summary,
    delta_signal: entry.delta_signal,
    delta_pct: entry.delta_pct,
  };
}

export function SectionSnapshotDiff({
  sectionId,
  data,
}: {
  readonly sectionId: string;
  readonly data: ReportAnalysisData;
}) {
  const comparisons = data.comparisons ?? null;
  const changelog = data.changelog ?? null;
  if (!comparisons && !changelog) return null;

  const items =
    comparisons
      ?.filter((c) => c.section_id === sectionId)
      .filter((c) => c.delta_signal !== "stable")
      .map(toItemView) ?? [];
  const entries =
    changelog?.filter((e) => e.section_id === sectionId).map(toEntryView) ?? [];

  if (items.length === 0 && entries.length === 0) return null;

  return (
    <div data-testid={`section-snapshot-diff-${sectionId}`}>
      <ComparisonItemsBlock items={items} />
      <SnapshotChangelogList entries={entries} />
    </div>
  );
}
