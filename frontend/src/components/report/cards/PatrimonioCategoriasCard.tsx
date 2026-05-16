import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import type { PatrimonioData } from "@/types/report-analysis";

interface PatrimonioCategoriasCardProps {
  patrimonio: PatrimonioData | undefined;
}

/** F9 · F2.A · S1 — Card "Composição Patrimonial por Categoria".
 *
 * Consome patrimonio.composicao (ou tabela_categorias como fallback).
 */
export function PatrimonioCategoriasCard({
  patrimonio,
}: PatrimonioCategoriasCardProps) {
  const allRows =
    patrimonio?.composicao ?? patrimonio?.tabela_categorias ?? [];
  // ADR-215 P5: esconde linha "Residência" R$ 0,00 (confusão "zero ≠
  // dado ausente"). Quando o usuário marca a residência via MembersTab,
  // ela passa a aparecer com valor real (lazy split do P3).
  const rows = allRows.filter(
    (row) => !(row.categoria === "Residência" && row.valor === 0),
  );
  const total = patrimonio?.bruto ?? 0;

  if (rows.length === 0) {
    return (
      <ReportCard variant="feature" title="Composição Patrimonial">
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Sem dados de composição patrimonial neste período.
        </p>
      </ReportCard>
    );
  }

  return (
    <ReportCard variant="feature" title="Composição Patrimonial">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--surface-border)] text-left">
              <th className="pb-2 font-display font-semibold">Categoria</th>
              <th className="pb-2 text-right font-display font-semibold">
                Valor
              </th>
              <th className="pb-2 text-right font-display font-semibold">%</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr
                key={`categoria-${idx}`}
                className="border-b border-[var(--surface-border)]/40 last:border-0"
              >
                <td className="py-2">{row.categoria}</td>
                <td className="py-2 text-right">
                  <MonetaryValue value={row.valor} />
                </td>
                <td className="py-2 text-right font-mono tabular-nums text-[var(--surface-muted-foreground)]">
                  {row.pct.toFixed(1)}%
                </td>
              </tr>
            ))}
            <tr className="font-semibold">
              <td className="pt-3">Total Bruto</td>
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
