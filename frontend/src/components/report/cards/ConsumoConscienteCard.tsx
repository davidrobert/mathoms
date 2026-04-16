import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import type { ConsumoConscienteData } from "@/types/report-analysis";

/** F9 · F2.B · S2 — Card "Consumo Consciente".
 *  Resume gastos pontuais ≥ R$2k, folga mensal, teto sugerido.
 */
export function ConsumoConscienteCard({
  consumo,
}: {
  consumo: ConsumoConscienteData | undefined;
}) {
  if (!consumo) {
    return (
      <ReportCard variant="success" title="Consumo Consciente">
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Sem dados de consumo consciente.
        </p>
      </ReportCard>
    );
  }

  return (
    <ReportCard variant="success" title="Consumo Consciente">
      <div className="space-y-4">
        <dl className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
          <div>
            <dt className="text-[var(--surface-muted-foreground)]">
              Gastos pontuais
            </dt>
            <dd className="mt-1 text-lg font-semibold">
              <MonetaryValue value={consumo.total_pontuais} />
            </dd>
          </div>
          <div>
            <dt className="text-[var(--surface-muted-foreground)]">
              Equiv. meses de aporte
            </dt>
            <dd className="mt-1 text-lg font-semibold font-mono tabular-nums">
              {consumo.equivalente_meses_aporte?.toFixed(1).replace(".", ",") ?? "—"}
            </dd>
          </div>
          <div>
            <dt className="text-[var(--surface-muted-foreground)]">Folga mensal</dt>
            <dd className="mt-1 text-lg font-semibold">
              <MonetaryValue value={consumo.folga_mensal} />
            </dd>
            <dd className="text-xs text-[var(--surface-muted-foreground)]">
              {consumo.folga_pct?.toFixed(0) ?? "—"}% da receita
            </dd>
          </div>
          <div>
            <dt className="text-[var(--surface-muted-foreground)]">
              Teto sugerido
            </dt>
            <dd className="mt-1 text-lg font-semibold">
              <MonetaryValue value={consumo.teto_sugerido} />
            </dd>
          </div>
        </dl>
        {consumo.analise && (
          <p className="rounded-md bg-[var(--surface-muted)] p-3 text-sm text-[var(--surface-muted-foreground)]">
            {consumo.analise}
          </p>
        )}
      </div>
    </ReportCard>
  );
}
