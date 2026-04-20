import { ReportCard } from "../ReportCard";

interface NarrativeChartCardProps {
  chartId: string;
  title: string;
  narratives: Record<string, unknown> | undefined;
  size?: "full" | "half";
}

/** F9 · F2.C–G — Card genérico para charts cujo dado é narrativo
 *  (apenas `context` + `conclusion`, sem datasets para Recharts).
 *
 *  Cobre a maioria dos charts de S3–S10 que vieram do e6_render.py
 *  como blocos de texto contextualizados.
 */
export function NarrativeChartCard({
  chartId,
  title,
  narratives,
  size = "full",
}: NarrativeChartCardProps) {
  const chart = narratives?.[chartId] as
    | { context?: string; conclusion?: string }
    | undefined;

  if (!chart?.context && !chart?.conclusion) {
    return null;
  }

  return (
    <ReportCard variant="neutral" title={title} size={size}>
      <div className="space-y-3">
        {chart.context && (
          <p className="text-sm text-[var(--surface-muted-foreground)]">
            {chart.context}
          </p>
        )}
        {chart.conclusion && (
          <p className="text-sm font-medium text-[var(--surface-foreground)]">
            {chart.conclusion}
          </p>
        )}
      </div>
    </ReportCard>
  );
}
