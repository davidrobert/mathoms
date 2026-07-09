import { ReportCard } from "../ReportCard";
import type { DiagnosticoComportamental } from "@/types/report-analysis";

/** F9 · F2.B · S2 — Card "Diagnóstico Comportamental".
 *  Tabela compacta: Padrão | Evidência | Mudança Sugerida.
 */
export function DiagnosticoComportamentalCard({
  diagnostico,
}: {
  diagnostico: DiagnosticoComportamental[] | undefined;
}) {
  const items = diagnostico ?? [];

  return (
    <ReportCard
      variant="primary"
      size="half"
      title="Diagnóstico Comportamental"
    >
      {items.length === 0 ? (
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Nenhum padrão comportamental identificado.
        </p>
      ) : (
        <>
          <p className="mb-3 text-xs text-[var(--surface-muted-foreground)]">
            {items.length} padrão(ões) identificado(s) com base nas transações do período
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--surface-border)] text-left text-xs uppercase tracking-wider text-[var(--surface-muted-foreground)]">
                  <th scope="col" className="pb-2 font-semibold">Padrão</th>
                  <th scope="col" className="pb-2 font-semibold">Evidência</th>
                  <th scope="col" className="pb-2 font-semibold">Mudança Sugerida</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item, idx) => (
                  <tr
                    key={idx}
                    className="border-b border-[var(--surface-border)]/40 last:border-0"
                  >
                    <td className="py-2 pr-3 font-medium text-[var(--surface-foreground)]">
                      {item.padrao}
                    </td>
                    <td className="py-2 pr-3 text-xs text-[var(--surface-muted-foreground)]">
                      {item.evidencia ?? "—"}
                    </td>
                    <td className="py-2 text-xs text-[var(--brand-primary)]">
                      {item.mudanca_sugerida ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </ReportCard>
  );
}
