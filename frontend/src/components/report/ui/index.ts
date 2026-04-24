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

export { PontoForteItem, PontosFortesList } from "./PontoForteItem";
export type { PontoForteItemProps } from "./PontoForteItem";

export { CollapsibleSectionHeader } from "./CollapsibleSectionHeader";

export { SplitCards, TwoColCards } from "./SplitCards";

export { ComparisonBlock } from "./ComparisonBlock";
export type { ComparisonSide } from "./ComparisonBlock";

export { PriorityBadge } from "./badges/PriorityBadge";
export type { PriorityLevel } from "./badges/PriorityBadge";

export { DeadlineBadge, deadlineStatus } from "./badges/DeadlineBadge";
export type { DeadlineStatus } from "./badges/DeadlineBadge";

export { EffortBadge } from "./badges/EffortBadge";
export type { Effort } from "./badges/EffortBadge";

export { Timeline } from "./Timeline";
export type { TimelineItem, TimelineStatus } from "./Timeline";

export { ChangelogList } from "./ChangelogList";
export type { ChangelogEntry } from "./ChangelogList";

export { Kanban } from "./kanban/Kanban";
export type { KanbanItem, KanbanColumn } from "./kanban/Kanban";

export { NotasCard } from "./NotasCard";
export type { NotasCardProps, NotasSaveState } from "./NotasCard";

export { NotasInsightsGrid, NotasInsightCard } from "./NotasInsightsGrid";
export type { NotasInsightCardProps } from "./NotasInsightsGrid";

// Re-export existing ReportCard for symmetry
export { ReportCard } from "../ReportCard";
