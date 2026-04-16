import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import type { FluxoCaixaSummary } from "@/types/report-analysis";

const FONTE_LABELS: Record<string, string> = {
  receita_clt: "CLT",
  receita_pj: "PJ",
  receita_aluguel: "Aluguéis",
  receita_investimento: "Rendimentos de Investimento",
  outras_receitas: "Outras receitas",
};

/** F9 · F2.A · S1 — Card "Receitas por Fonte".
 *
 * Substitui build_receitas_fonte_card() do e6_render.py. Fica em S1
 * por convenção histórica do layout (embora o dado venha de fluxo_caixa).
 */
export function ReceitasFonteCard({
  fluxo,
}: {
  fluxo: FluxoCaixaSummary | undefined;
}) {
  const porFonte = fluxo?.por_fonte ?? {};
  const entries = Object.entries(porFonte).filter(
    ([, v]) => typeof v === "number" && v > 0,
  ) as Array<[string, number]>;

  const total = entries.reduce((sum, [, v]) => sum + v, 0);
  entries.sort((a, b) => b[1] - a[1]);

  if (entries.length === 0) {
    return (
      <ReportCard variant="feature" title="Receitas por Fonte">
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Sem dados de receitas neste período.
        </p>
      </ReportCard>
    );
  }

  return (
    <ReportCard variant="feature" title="Receitas por Fonte">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--surface-border)] text-left">
              <th className="pb-2 font-display font-semibold">Fonte</th>
              <th className="pb-2 text-right font-display font-semibold">
                Total
              </th>
              <th className="pb-2 text-right font-display font-semibold">%</th>
            </tr>
          </thead>
          <tbody>
            {entries.map(([key, value]) => {
              const pct = total > 0 ? (value / total) * 100 : 0;
              return (
                <tr
                  key={key}
                  className="border-b border-[var(--surface-border)]/40 last:border-0"
                >
                  <td className="py-2">{FONTE_LABELS[key] ?? key}</td>
                  <td className="py-2 text-right">
                    <MonetaryValue value={value} />
                  </td>
                  <td className="py-2 text-right font-mono tabular-nums text-[var(--surface-muted-foreground)]">
                    {pct.toFixed(1)}%
                  </td>
                </tr>
              );
            })}
            <tr className="font-semibold">
              <td className="pt-3">Total</td>
              <td className="pt-3 text-right">
                <MonetaryValue value={total} />
              </td>
              <td className="pt-3 text-right font-mono tabular-nums">100,0%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </ReportCard>
  );
}
