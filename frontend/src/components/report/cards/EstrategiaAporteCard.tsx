import { formatCurrency } from "@/lib/format";
import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";

interface DestinoAporte {
  destino: string;
  valor: number;
  pct: number;
  objetivo?: string;
  liquidez?: string;
  moeda?: "BRL" | "USD" | string;
}

export interface EstrategiaAporteData {
  total_aporte?: number;
  dia_aporte?: number;
  periodo_inicio?: string;
  destinos?: DestinoAporte[];
  pct_brl?: number;
  pct_usd?: number;
  resumo_brl?: string;
  resumo_usd?: string;
}

interface EstrategiaAporteCardProps {
  estrategia?: EstrategiaAporteData;
  /** Fallback: cenários IF (legado) */
  goals?: Record<string, unknown>;
  cenarios?: { aportes?: number[]; labels?: string[] };
}

/** F9 · F2.C · S3 — Card "Estratégia de Aporte e Alocação".
 *  Tabela de destinos com objetivo e liquidez + mini-cards BRL vs USD.
 *  Fallback para cenários IF quando estrategia_aporte não disponível.
 */
export function EstrategiaAporteCard({
  estrategia,
  goals,
  cenarios,
}: EstrategiaAporteCardProps) {
  const destinos = estrategia?.destinos ?? [];
  const hasRichData = destinos.length > 0;

  if (hasRichData) {
    const total = estrategia!.total_aporte ?? destinos.reduce((s, d) => s + d.valor, 0);
    const subtitle = [
      estrategia?.total_aporte !== undefined
        ? `Aporte mensal de ${formatCurrency(total, "BRL", { minimumFractionDigits: 0, maximumFractionDigits: 3 })} no dia ${estrategia.dia_aporte ?? "?"} de cada mês`
        : null,
      estrategia?.periodo_inicio ? `A partir de ${estrategia.periodo_inicio}` : null,
    ]
      .filter(Boolean)
      .join(". ");

    return (
      <ReportCard variant="highlight" title="Estratégia de Aporte e Alocação">
        {subtitle && (
          <p className="mb-4 text-sm text-[var(--surface-muted-foreground)]">{subtitle}</p>
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--surface-border)] text-left text-xs uppercase tracking-wider text-[var(--surface-muted-foreground)]">
                <th scope="col" className="pb-2 font-semibold">Destino</th>
                <th scope="col" className="pb-2 text-right font-semibold">Valor/mês</th>
                <th scope="col" className="pb-2 text-right font-semibold">%</th>
                <th scope="col" className="hidden pb-2 font-semibold sm:table-cell">Objetivo</th>
                <th scope="col" className="hidden pb-2 font-semibold sm:table-cell">Liquidez</th>
              </tr>
            </thead>
            <tbody>
              {destinos.map((d, i) => (
                <tr
                  key={i}
                  className="border-b border-[var(--surface-border)]/40 last:border-0"
                >
                  <td className="py-2 pr-3 font-medium">{d.destino}</td>
                  <td className="py-2 pr-2 text-right">
                    <MonetaryValue value={d.valor} />
                  </td>
                  <td className="py-2 pr-3 text-right font-mono tabular-nums text-[var(--surface-muted-foreground)]">
                    {d.pct}%
                  </td>
                  <td className="hidden py-2 pr-3 text-xs text-[var(--surface-muted-foreground)] sm:table-cell">
                    {d.objetivo ?? "—"}
                  </td>
                  <td className="hidden py-2 text-xs text-[var(--surface-muted-foreground)] sm:table-cell">
                    {d.liquidez ?? "—"}
                  </td>
                </tr>
              ))}
              <tr className="font-semibold">
                <td className="pt-3">Total</td>
                <td className="pt-3 text-right">
                  <MonetaryValue value={total} />
                </td>
                <td className="pt-3 text-right font-mono tabular-nums">100%</td>
                <td className="hidden pt-3 sm:table-cell" />
                <td className="hidden pt-3 sm:table-cell" />
              </tr>
            </tbody>
          </table>
        </div>

        {(estrategia?.pct_brl !== undefined || estrategia?.pct_usd !== undefined) && (
          <div className="mt-4 grid grid-cols-2 gap-3">
            <div className="rounded-[var(--radius-md)] border border-[var(--surface-border)] bg-[color-mix(in_srgb,var(--semantic-gain)_8%,var(--surface-card))] p-3">
              <p className="text-sm font-semibold text-[var(--semantic-gain)]">
                {estrategia?.pct_brl ?? 0}% em BRL
              </p>
              {estrategia?.resumo_brl && (
                <p className="mt-1 text-xs text-[var(--surface-muted-foreground)]">
                  {estrategia.resumo_brl}
                </p>
              )}
            </div>
            <div className="rounded-[var(--radius-md)] border border-[var(--surface-border)] bg-[color-mix(in_srgb,var(--brand-primary)_8%,var(--surface-card))] p-3">
              <p className="text-sm font-semibold text-[var(--brand-primary)]">
                {estrategia?.pct_usd ?? 0}% em USD
              </p>
              {estrategia?.resumo_usd && (
                <p className="mt-1 text-xs text-[var(--surface-muted-foreground)]">
                  {estrategia.resumo_usd}
                </p>
              )}
            </div>
          </div>
        )}
      </ReportCard>
    );
  }

  // Fallback: IF scenarios (legado)
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
                  <th scope="col" className="pb-2 font-display font-semibold">Cenário</th>
                  <th scope="col" className="pb-2 text-right font-display font-semibold">Aporte/mês</th>
                </tr>
              </thead>
              <tbody>
                {labels.map((label, i) => (
                  <tr key={label} className="border-b border-[var(--surface-border)]/40 last:border-0">
                    <td className="py-2">{label}</td>
                    <td className="py-2 text-right">
                      <MonetaryValue value={aportes[i]} />
                    </td>
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
