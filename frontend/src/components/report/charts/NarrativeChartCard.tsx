import { ReportCard } from "../ReportCard";

interface NarrativeChartCardProps {
  chartId: string;
  title: string;
  narratives: Record<string, unknown> | undefined;
  size?: "full" | "half";
  /** ADR-117/122 · Fase 7 — fallback determinístico quando E5.N não
   *  gerou narrativa. Normalmente `deriveChartConclusion(chartId, data)`. */
  fallbackConclusion?: string | null;
}

/** F9 · F2.C–G — Card genérico para charts cujo dado é narrativo
 *  (apenas `context` + `conclusion`, sem datasets para Recharts).
 */
export function NarrativeChartCard({
  chartId,
  title,
  narratives,
  size = "full",
  fallbackConclusion,
}: NarrativeChartCardProps) {
  const chart = narratives?.[chartId] as
    | { context?: string; conclusion?: string }
    | undefined;

  const context = chart?.context;
  const conclusion = chart?.conclusion ?? fallbackConclusion ?? undefined;

  if (!context && !conclusion) {
    return null;
  }

  return (
    <ReportCard variant="neutral" title={title} size={size}>
      <div className="space-y-3">
        {context && (
          <p className="text-sm text-[var(--surface-muted-foreground)]">
            {context}
          </p>
        )}
        {conclusion && (
          <p className="text-sm font-medium text-[var(--surface-foreground)]">
            {conclusion}
          </p>
        )}
      </div>
    </ReportCard>
  );
}
