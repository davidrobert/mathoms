import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import type { EndividamentoData } from "@/types/report-analysis";

/** F9 · F2.A · S1 — Card "Endividamento".
 *
 * Mostra total, % do patrimônio e lista de dívidas (se houver). Quando
 * total_dividas=0 celebra a situação com mensagem positiva.
 */
export function EndividamentoCard({
  endividamento,
}: {
  endividamento: EndividamentoData | undefined;
}) {
  const total = endividamento?.total_dividas ?? 0;
  const pct = endividamento?.percentual_patrimonio ?? 0;
  const dividas = endividamento?.dividas ?? [];
  const semDividas = total === 0 && dividas.length === 0;

  return (
    <ReportCard
      variant={semDividas ? "success" : total > 0 ? "warn" : "feature"}
      size="half"
      title="Endividamento"
    >
      {semDividas ? (
        <div className="space-y-2">
          <MonetaryValue value={0} size="kpi" className="text-[var(--semantic-gain)]" />
          <p className="text-sm text-[var(--surface-muted-foreground)]">
            {endividamento?.detalhe ?? "Sem dívidas identificadas neste período."}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-xs uppercase tracking-wider text-[var(--surface-muted-foreground)]">
                Total de dívidas
              </p>
              <MonetaryValue value={total} size="kpi" className="mt-1" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-wider text-[var(--surface-muted-foreground)]">
                % do patrimônio
              </p>
              <p className="mt-1 font-mono text-2xl font-semibold tabular-nums">
                {pct.toFixed(1)}%
              </p>
            </div>
          </div>

          {dividas.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--surface-border)] text-left">
                    <th className="pb-2 font-display font-semibold">Descrição</th>
                    <th className="pb-2 text-right font-display font-semibold">
                      Valor
                    </th>
                    <th className="pb-2 text-right font-display font-semibold">
                      Taxa
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {dividas.map((d, idx) => (
                    <tr
                      key={`divida-${idx}`}
                      className="border-b border-[var(--surface-border)]/40 last:border-0"
                    >
                      <td className="py-2">{d.descricao}</td>
                      <td className="py-2 text-right">
                        <MonetaryValue value={d.valor} />
                      </td>
                      <td className="py-2 text-right font-mono tabular-nums text-[var(--surface-muted-foreground)]">
                        {d.taxa !== undefined
                          ? `${d.taxa.toFixed(2)}%`
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </ReportCard>
  );
}
