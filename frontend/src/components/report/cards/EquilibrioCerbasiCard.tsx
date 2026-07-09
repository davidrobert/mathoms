import { ReportCard } from "../ReportCard";
import type { EquilibrioCerbasiData } from "@/types/report-analysis";

/** F9 · F2.B · S2 — Card "Equilíbrio Cerbasi".
 *  Mostra % presente vs futuro e classificação (Gustavo Cerbasi framework).
 */
export function EquilibrioCerbasiCard({
  equilibrio,
}: {
  equilibrio: EquilibrioCerbasiData | undefined;
}) {
  if (!equilibrio) {
    return (
      <ReportCard variant="highlight" size="half" title="Equilíbrio entre Presente e Futuro">
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Dados de equilíbrio não disponíveis.
        </p>
      </ReportCard>
    );
  }

  const pctPresente = equilibrio.pct_presente ?? 0;
  const pctFuturo = equilibrio.pct_futuro ?? 0;

  return (
    <ReportCard variant="highlight" size="half" title="Equilíbrio entre Presente e Futuro">
      <div className="space-y-4">
        {/* Barra visual presente vs futuro */}
        <div>
          <div className="flex justify-between text-xs text-[var(--surface-muted-foreground)]">
            <span>Presente ({pctPresente}%)</span>
            <span>Futuro ({pctFuturo}%)</span>
          </div>
          <div
            className="mt-1 flex h-4 overflow-hidden rounded-full"
            role="img"
            aria-label={`Distribuição do fluxo: ${pctPresente}% para o presente, ${pctFuturo}% para o futuro`}
          >
            <div
              className="bg-[var(--brand-primary)] transition-[width]"
              style={{ width: `${pctPresente}%` }}
            />
            <div
              className="bg-[var(--brand-accent)] transition-[width]"
              style={{ width: `${pctFuturo}%` }}
            />
          </div>
        </div>

        {/* Classificação */}
        <div className="text-center">
          <p className="font-display text-lg font-bold text-[var(--brand-primary)]">
            {equilibrio.classificacao ?? "—"}
          </p>
        </div>

        {/* Detalhe */}
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <dt className="text-xs uppercase tracking-wider text-[var(--surface-muted-foreground)]">
              Presente
            </dt>
            <dd className="mt-1 font-medium">{equilibrio.presente ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wider text-[var(--surface-muted-foreground)]">
              Futuro
            </dt>
            <dd className="mt-1 font-medium">{equilibrio.futuro ?? "—"}</dd>
          </div>
        </dl>
      </div>
    </ReportCard>
  );
}
