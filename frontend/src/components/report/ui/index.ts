/** ADR-117 · Fase 3 — barrel de primitivos UI do relatório.
 *
 * Consumidores:
 *   import { Alert, Badge, KpiGrid, ScoreCard } from "@/components/report/ui";
 */
export { Alert } from "./Alert";
export type { AlertSeverity } from "./Alert";

export { Badge } from "./Badge";
export type { BadgeColor } from "./Badge";

export { IconBadge } from "./IconBadge";
export type { IconBadgeColor } from "./IconBadge";

export { SectionDivider } from "./SectionDivider";

export { KpiCard, KpiGrid, KpiStrip } from "./Kpi";
export type { KpiCardProps, KpiStripItem, KpiTone, KpiAccent } from "./Kpi";

export { ScoreCard } from "./ScoreCard";
export type { ScoreCardProps, ScoreBreakdownRow, ScoreClasse } from "./ScoreCard";

export { PeriodToggle } from "./PeriodToggle";
export type { Period, PeriodToggleProps } from "./PeriodToggle";

export { PontoForteItem, PontosFortesList } from "./PontoForteItem";
export type { PontoForteItemProps } from "./PontoForteItem";

export { CollapsibleSectionHeader } from "./CollapsibleSectionHeader";

export { SplitCards, TwoColCards } from "./SplitCards";

export { ComparisonBlock } from "./ComparisonBlock";
export type { ComparisonSide } from "./ComparisonBlock";

export { ComparisonItemsBlock } from "./ComparisonItemsBlock";
export type { ComparisonItemView, DeltaSignal } from "./ComparisonItemsBlock";

export { SnapshotChangelogList } from "./SnapshotChangelogList";
export type {
  SnapshotChangelogEntryView,
  ChangelogDeltaSignal,
} from "./SnapshotChangelogList";

export { PriorityBadge } from "./badges/PriorityBadge";
export type { PriorityLevel } from "./badges/PriorityBadge";

export { DeadlineBadge, deadlineStatus } from "./badges/DeadlineBadge";
export type { DeadlineStatus } from "./badges/DeadlineBadge";

export { EffortBadge } from "./badges/EffortBadge";
export type { Effort } from "./badges/EffortBadge";

export { ChangelogList } from "./ChangelogList";
export type { ChangelogEntry } from "./ChangelogList";

export { CpfField } from "./CpfField";
export type { CpfFieldProps } from "./CpfField";

// Re-export existing ReportCard for symmetry
export { ReportCard } from "../ReportCard";
