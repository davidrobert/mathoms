import { Construction } from "lucide-react";
import { ReportCard } from "./ReportCard";

interface ReportSectionStubProps {
  cardIds: string[];
  chartIds: string[];
}

/** F9 · F1.1 — Stub mostrado enquanto um card ainda não migrou para React.
 *
 * Estratégia de migração por lotes (2.A–2.H): cada lote substitui alguns
 * stubs por componentes reais. Não é um erro — é progresso visível.
 */
export function ReportSectionStub({
  cardIds,
  chartIds,
}: ReportSectionStubProps) {
  return (
    <ReportCard variant="neutral" size="full">
      <div className="flex flex-col gap-4">
        <div className="flex items-start gap-3">
          <Construction className="mt-0.5 h-5 w-5 shrink-0 text-[var(--brand-neutral)]" />
          <div className="space-y-1">
            <p className="font-display font-medium text-[var(--surface-foreground)]">
              Conteúdo em migração para a nova experiência
            </p>
            <p className="text-sm text-[var(--surface-muted-foreground)]">
              Esta seção ainda está sendo migrada para a visualização nativa.
            </p>
          </div>
        </div>

        {(cardIds.length > 0 || chartIds.length > 0) && (
          <div className="rounded-md bg-[var(--surface-muted)] px-4 py-3 text-xs font-mono text-[var(--surface-muted-foreground)]">
            {cardIds.length > 0 && (
              <div>cards: {cardIds.join(", ")}</div>
            )}
            {chartIds.length > 0 && (
              <div>charts: {chartIds.join(", ")}</div>
            )}
          </div>
        )}
      </div>
    </ReportCard>
  );
}
