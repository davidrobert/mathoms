import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";

export interface InvestimentosClasseData {
  tabela_classes?: Array<{ categoria: string; valor: number; pct: number }>;
  total?: number;
}

interface InvestimentosClasseCardProps {
  investimentos: InvestimentosClasseData | undefined;
}

/** F9 · F2.C · S3 — Card "Investimentos por Classe de Ativo". */
export function InvestimentosClasseCard({ investimentos }: InvestimentosClasseCardProps) {
  const rows = investimentos?.tabela_classes ?? [];
  const total = investimentos?.total ?? 0;

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
              <th className="pb-2 font-display font-semibold">Classe</th>
              <th className="pb-2 text-right font-display font-semibold">Valor</th>
              <th className="pb-2 text-right font-display font-semibold">%</th>
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
    </ReportCard>
  );
}
