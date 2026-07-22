import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";

export interface InvestimentosClasseData {
  tabela_classes?: Array<{
    categoria: string;
    valor: number;
    /** Base: total investido (financeiro + imóveis de investimento) — A37.l9. */
    pct: number;
    /** Base: carteira financeira (ex-imóveis físicos); null fora da base — A37.l9. */
    pct_carteira_financeira?: number | null;
  }>;
  total?: number;
  /** Decomposição por construção: total = total_financeiro + total_imoveis_investimento. */
  total_financeiro?: number;
  total_imoveis_investimento?: number;
}

interface InvestimentosClasseCardProps {
  investimentos: InvestimentosClasseData | undefined;
}

/** F9 · F2.C · S3 — Card "Investimentos por Classe de Ativo". */
export function InvestimentosClasseCard({ investimentos }: InvestimentosClasseCardProps) {
  const rows = investimentos?.tabela_classes ?? [];
  const total = investimentos?.total ?? 0;
  const totalFinanceiro = investimentos?.total_financeiro;
  const totalImoveis = investimentos?.total_imoveis_investimento;
  const hasDecomposicao =
    typeof totalFinanceiro === "number" && typeof totalImoveis === "number" && totalImoveis > 0;

  if (rows.length === 0) {
    return (
      <ReportCard variant="feature" title="Investimentos por Classe">
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Sem posições de investimento detalhadas neste período.
          {total > 0 && (
            <>
              {" "}
              Total investido:{" "}
              <MonetaryValue value={total} provenance={{ fieldId: "investimentos.total" }} />.
            </>
          )}
        </p>
      </ReportCard>
    );
  }

  return (
    <ReportCard variant="feature" title="Investimentos por Classe">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--surface-border)] text-left">
              <th scope="col" className="pb-2 font-display font-semibold">Classe</th>
              <th scope="col" className="pb-2 text-right font-display font-semibold">Valor</th>
              <th scope="col" className="pb-2 text-right font-display font-semibold">% do total investido</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={`classe-${i}`} className="border-b border-[var(--surface-border)]/40 last:border-0">
                <td className="py-2">{r.categoria}</td>
                <td className="py-2 text-right"><MonetaryValue value={r.valor} /></td>
                <td className="py-2 text-right font-mono tabular-nums text-[var(--surface-muted-foreground)]">{r.pct.toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {hasDecomposicao && (
        <p className="mt-3 text-xs text-[var(--surface-muted-foreground)]">
          Base: total investido = carteira financeira (
          <MonetaryValue value={totalFinanceiro} />) + imóveis de investimento (
          <MonetaryValue value={totalImoveis} />).
        </p>
      )}
    </ReportCard>
  );
}
