import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import {
  visibleCompositionRows,
  type VisibleCompositionRow,
} from "../utils/visibleCompositionRows";
import type { PatrimonioData } from "@/types/report-analysis";

interface PatrimonioCategoriasCardProps {
  patrimonio: PatrimonioData | undefined;
}

/** Célula de valor por estado — o `—` do não-apurado é a diferença que o
 *  RV6-23 pedia: zero medido e zero por falta de fonte deixam de imprimir
 *  igual. */
function ValorCell({ row }: { row: VisibleCompositionRow }) {
  // O travessão sozinho não é lido — quem depende de leitor de tela ouviria
  // uma célula vazia, que é a mesma ambiguidade que a lane fecha no visual.
  if (row.state === "nao_apurado") {
    return (
      <>
        <span aria-hidden="true">—</span>
        <span className="sr-only">Sem fonte apurada</span>
      </>
    );
  }
  // O valor negativo já é anunciado pelo próprio número; o `*` é só o ponteiro
  // visual para a nota de rodapé.
  return (
    <>
      <MonetaryValue value={row.valor} />
      {row.state === "negativo" ? <span aria-hidden="true">&nbsp;*</span> : null}
    </>
  );
}

/** F9 · F2.A · S1 — Card "Composição Patrimonial por Categoria".
 *
 * Consome patrimonio.composicao (ou tabela_categorias como fallback), pelo
 * predicado único da A40.l71 — o filtro da ADR-215 P5 mora lá.
 */
export function PatrimonioCategoriasCard({
  patrimonio,
}: PatrimonioCategoriasCardProps) {
  const rows = visibleCompositionRows(patrimonio);
  const total = patrimonio?.bruto ?? 0;
  const hasNegativo = rows.some((row) => row.state === "negativo");
  const hasNaoApurado = rows.some((row) => row.state === "nao_apurado");

  if (rows.length === 0) {
    return (
      <ReportCard variant="feature" title="Composição Patrimonial por Categoria">
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Sem dados de composição patrimonial neste período.
        </p>
      </ReportCard>
    );
  }

  return (
    <ReportCard variant="feature" title="Composição Patrimonial por Categoria">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--surface-border)] text-left">
              <th scope="col" className="pb-2 font-display font-semibold">Categoria</th>
              <th scope="col" className="pb-2 text-right font-display font-semibold">
                Valor
              </th>
              <th scope="col" className="pb-2 text-right font-display font-semibold">% do bruto</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr
                key={`categoria-${idx}`}
                className="border-b border-[var(--surface-border)]/40 last:border-0"
                data-composition-state={row.state}
              >
                <td className="py-2">{row.categoria}</td>
                <td className="py-2 text-right">
                  <ValorCell row={row} />
                </td>
                <td className="py-2 text-right font-mono tabular-nums text-[var(--surface-muted-foreground)]">
                  {row.state === "nao_apurado" ? "—" : `${row.pct.toFixed(1)}%`}
                </td>
              </tr>
            ))}
            <tr className="font-semibold">
              <td className="pt-3">Total Bruto</td>
              <td className="pt-3 text-right">
                <MonetaryValue value={total} provenance={{ fieldId: "patrimonio.bruto" }} />
              </td>
              <td className="pt-3 text-right font-mono tabular-nums">100,0%</td>
            </tr>
          </tbody>
        </table>
      </div>
      {hasNegativo || hasNaoApurado ? (
        <p className="mt-3 text-xs text-[var(--surface-muted-foreground)]">
          {hasNegativo
            ? "* Balde com valor negativo — dado em conferência, não some do total. "
            : null}
          {hasNaoApurado ? "— Sem fonte apurada para esta categoria." : null}
        </p>
      ) : null}
    </ReportCard>
  );
}
