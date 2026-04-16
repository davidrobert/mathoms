import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import type { OrcamentoProspectivoData } from "@/types/report-analysis";

const CATEGORY_LABELS: Record<string, string> = {
  assinaturas: "Assinaturas",
  seguros: "Seguros",
  financeiro: "Financeiro",
  impostos: "Impostos",
  nao_identificado: "Não identificado",
  reserva_desejos: "Reserva de desejos",
  transporte: "Transporte",
  financiamentos: "Financiamentos",
  moradia: "Moradia",
  alimentacao: "Alimentação",
  suporte_familiar: "Suporte familiar",
  saude: "Saúde",
  lazer_viagens: "Lazer e viagens",
  vestuario: "Vestuário",
  educacao: "Educação",
  servicos_domesticos: "Serviços domésticos",
  melhoria_reforma: "Melhoria e reforma",
};

/** F9 · F2.B · S2 — Card "Orçamento Prospectivo".
 *  Tabela com tetos médios por categoria de despesa.
 */
export function OrcamentoProspectivoCard({
  orcamento,
}: {
  orcamento: OrcamentoProspectivoData | undefined;
}) {
  const categorias = orcamento?.categorias ?? {};
  const entries = Object.entries(categorias)
    .filter(([, v]) => v > 0)
    .sort(([, a], [, b]) => b - a);
  const total = orcamento?.total ?? 0;

  return (
    <ReportCard variant="feature" title="Orçamento Prospectivo Mensal">
      {entries.length === 0 ? (
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Sem dados de orçamento neste período.
        </p>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--surface-border)] text-left">
                  <th className="pb-2 font-display font-semibold">Categoria</th>
                  <th className="pb-2 text-right font-display font-semibold">
                    Teto/mês
                  </th>
                  <th className="pb-2 text-right font-display font-semibold">%</th>
                </tr>
              </thead>
              <tbody>
                {entries.map(([key, value]) => (
                  <tr
                    key={key}
                    className="border-b border-[var(--surface-border)]/40 last:border-0"
                  >
                    <td className="py-2">{CATEGORY_LABELS[key] ?? key}</td>
                    <td className="py-2 text-right">
                      <MonetaryValue value={value} />
                    </td>
                    <td className="py-2 text-right font-mono tabular-nums text-[var(--surface-muted-foreground)]">
                      {total > 0 ? ((value / total) * 100).toFixed(1) : "—"}%
                    </td>
                  </tr>
                ))}
                <tr className="font-semibold">
                  <td className="pt-3">Total</td>
                  <td className="pt-3 text-right">
                    <MonetaryValue value={total} />
                  </td>
                  <td className="pt-3 text-right font-mono tabular-nums">
                    100,0%
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          {orcamento?.legenda && (
            <p className="mt-3 text-xs italic text-[var(--surface-muted-foreground)]">
              {orcamento.legenda}
            </p>
          )}
        </>
      )}
    </ReportCard>
  );
}
