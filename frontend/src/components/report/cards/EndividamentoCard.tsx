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
          <p className="font-mono text-3xl font-semibold tabular-nums text-[var(--semantic-gain)]">
            R$ 0,00
          </p>
          <p className="text-sm text-[var(--surface-muted-foreground)]">
            {endividamento?.detalhe ?? "Sem dívidas identificadas neste período."}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <div>
            <p className="text-xs uppercase tracking-wider text-[var(--surface-muted-foreground)]">
              Total de dívidas
            </p>
            <p className="mt-1 font-mono text-3xl font-semibold tabular-nums">
              <MonetaryValue
                value={total}
                provenance={{ fieldId: "endividamento.total_dividas" }}
              />
            </p>
            <p className="mt-1 text-sm text-[var(--surface-muted-foreground)]">
              <span className="font-mono tabular-nums">
                {pct.toFixed(1).replace(".", ",")}%
              </span>{" "}
              do patrimônio
            </p>
          </div>

          {dividas.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--surface-border)] text-left">
                    <th scope="col" className="pb-2 font-display font-semibold">Descrição</th>
                    <th scope="col" className="pb-2 text-right font-display font-semibold">
                      Valor
                    </th>
                    <th scope="col" className="pb-2 text-right font-display font-semibold">
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
