import { ReportCard } from "../ReportCard";

/** S9-T04 (ADR-192 §D4) — Legenda 3ª dimensão para o bubble `bubble_riscos`.
 *
 * `mitigation_status` (verde coberto / amarelo parcial / vermelho descoberto)
 * é a cor de cada bolha. Tokens via `var(--semantic-*)` — sem hex literal.
 */
export interface MitigationLegendItem {
  status: "coberto" | "parcial" | "descoberto";
  label: string;
  count?: number;
}

interface NarrativeChartCardProps {
  chartId: string;
  title: string;
  narratives: Record<string, unknown> | undefined;
  size?: "full" | "half";
  /** ADR-117/122 · Fase 7 — fallback determinístico quando E5.N não
   *  gerou narrativa. Normalmente `deriveChartConclusion(chartId, data)`. */
  fallbackConclusion?: string | null;
  /** ADR-192 §D4 — legenda da 3ª dimensão (cor) do bubble.
   *  Renderizada quando presente; default oculta. */
  mitigationLegend?: MitigationLegendItem[];
}

const STATUS_COLOR: Record<MitigationLegendItem["status"], string> = {
  coberto: "var(--semantic-gain)",
  parcial: "var(--semantic-warning)",
  descoberto: "var(--semantic-loss)",
};

/** F9 · F2.C–G — Card genérico para charts cujo dado é narrativo
 *  (apenas `context` + `conclusion`, sem datasets para Recharts).
 */
export function NarrativeChartCard({
  chartId,
  title,
  narratives,
  size = "full",
  fallbackConclusion,
  mitigationLegend,
}: NarrativeChartCardProps) {
  const chart = narratives?.[chartId] as
    | { context?: string; conclusion?: string }
    | undefined;

  const context = chart?.context;
  const conclusion = chart?.conclusion ?? fallbackConclusion ?? undefined;

  if (!context && !conclusion && !mitigationLegend?.length) {
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
        {mitigationLegend && mitigationLegend.length > 0 && (
          <ul
            className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs"
            aria-label="Legenda de status de mitigação"
          >
            {mitigationLegend.map((item) => (
              <li key={item.status} className="flex items-center gap-1.5">
                <span
                  aria-hidden="true"
                  className="inline-block h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: STATUS_COLOR[item.status] }}
                />
                <span className="text-[var(--surface-foreground)]">
                  {item.label}
                  {item.count !== undefined && ` (${item.count})`}
                </span>
              </li>
            ))}
          </ul>
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
