import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";

interface EstrategiaAporteCardProps {
  goals: Record<string, unknown> | undefined;
  cenarios: { aportes?: number[]; labels?: string[] } | undefined;
}

/** F9 · F2.C · S3 — Card "Estratégia de Aportes".
 *  Mostra meta de aporte mensal para cada cenário IF.
 */
export function EstrategiaAporteCard({ goals, cenarios }: EstrategiaAporteCardProps) {
  const ifTrs = goals?.if_trs_monthly_value as number | undefined;
  const labels = cenarios?.labels ?? [];
  const aportes = cenarios?.aportes ?? [];

  return (
    <ReportCard variant="highlight" title="Estratégia de Aportes">
      <div className="space-y-4">
        {ifTrs !== undefined && (
          <div>
            <p className="text-xs uppercase tracking-wider text-[var(--surface-muted-foreground)]">
              Aporte mensal necessário (meta IF)
            </p>
            <p className="mt-1 text-2xl font-semibold">
              <MonetaryValue value={ifTrs} />
            </p>
          </div>
        )}
        {labels.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--surface-border)] text-left">
                  <th className="pb-2 font-display font-semibold">Cenário</th>
                  <th className="pb-2 text-right font-display font-semibold">Aporte/mês</th>
                </tr>
              </thead>
              <tbody>
                {labels.map((label, i) => (
                  <tr key={label} className="border-b border-[var(--surface-border)]/40 last:border-0">
                    <td className="py-2">{label}</td>
                    <td className="py-2 text-right"><MonetaryValue value={aportes[i]} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {!ifTrs && labels.length === 0 && (
          <p className="text-sm text-[var(--surface-muted-foreground)]">
            Meta de aporte não configurada.
          </p>
        )}
      </div>
    </ReportCard>
  );
}
