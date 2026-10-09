import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import { formatPercent } from "@/lib/format";

export interface InvestimentosClasseData {
  tabela_classes?: Array<{
    categoria: string;
    valor: number;
    /** Base: total investido (financeiro + imóveis de investimento) — A37.l9.
     *  `null` só em "Imóveis com uso não apurado": com valor e sem peso (ADR-444 D3). */
    pct: number | null;
    /** Base: carteira financeira (ex-imóveis físicos); null fora da base — A37.l9. */
    pct_carteira_financeira?: number | null;
  }>;
  total?: number;
  /** Decomposição por construção: total = total_financeiro + total_imoveis_investimento. */
  total_financeiro?: number;
  total_imoveis_investimento?: number;
  /** Fora do total investido (ADR-444 D3): total + este = Σ das linhas. */
  total_imoveis_uso_nao_apurado?: number;
}

interface InvestimentosClasseCardProps {
  investimentos: InvestimentosClasseData | undefined;
}

function PctCell({ pct }: { pct: number | null }) {
  if (pct !== null) return <>{formatPercent(pct)}</>;
  return (
    <>
      <span aria-hidden="true">—</span>
      <span className="sr-only">fora da base</span>
    </>
  );
}

function RodapeDaBase({
  totalFinanceiro,
  totalImoveis,
  totalSemPeso,
}: {
  totalFinanceiro?: number;
  totalImoveis?: number;
  totalSemPeso: number;
}) {
  const hasDecomposicao =
    typeof totalFinanceiro === "number" && typeof totalImoveis === "number" && totalImoveis > 0;
  return (
    <>
      {hasDecomposicao && (
        <p className="mt-3 text-xs text-[var(--surface-muted-foreground)]">
          Base: total investido = carteira financeira (
          <MonetaryValue value={totalFinanceiro} />) + imóveis de investimento (
          <MonetaryValue value={totalImoveis} />).
        </p>
      )}
      {totalSemPeso > 0 && (
        <p className="mt-1 text-xs text-[var(--surface-muted-foreground)]">
          Imóveis com uso não apurado (<MonetaryValue value={totalSemPeso} />) ficam fora
          da base.
        </p>
      )}
    </>
  );
}

/** F9 · F2.C · S3 — Card "Investimentos por Classe de Ativo". */
export function InvestimentosClasseCard({ investimentos }: InvestimentosClasseCardProps) {
  const rows = investimentos?.tabela_classes ?? [];
  const total = investimentos?.total ?? 0;
  const totalFinanceiro = investimentos?.total_financeiro;
  const totalImoveis = investimentos?.total_imoveis_investimento;
  const totalSemPeso = investimentos?.total_imoveis_uso_nao_apurado ?? 0;

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
                <td className="py-2 text-right font-mono tabular-nums text-[var(--surface-muted-foreground)]">
                  <PctCell pct={r.pct} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <RodapeDaBase
        totalFinanceiro={totalFinanceiro}
        totalImoveis={totalImoveis}
        totalSemPeso={totalSemPeso}
      />
    </ReportCard>
  );
}
