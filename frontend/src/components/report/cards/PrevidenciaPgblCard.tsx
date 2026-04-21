import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";

export interface PrevidenciaPgblData {
  status?: string;
  nota?: string;
  renda_tributavel_anual?: number;
  limite_pgbl_anual?: number;
  aporte_mensal?: number;
  aliquota_marginal?: number;
  economia_ir_anual?: number;
}

/** F9 · F2.E · S7 — Card "Previdência PGBL".
 *  Resumo do cálculo PGBL com economia de IR estimada.
 */
export function PrevidenciaPgblCard({
  previdencia,
}: {
  previdencia: PrevidenciaPgblData | undefined;
}) {
  if (!previdencia || previdencia.status === "Não aplicável") {
    return (
      <ReportCard variant="feature" title="Previdência PGBL">
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          PGBL não aplicável para este perfil tributário.
        </p>
      </ReportCard>
    );
  }

  return (
    <ReportCard variant="feature" title="Previdência PGBL">
      <div className="space-y-4">
        <dl className="grid grid-cols-2 gap-4 text-sm md:grid-cols-3">
          <div>
            <dt className="text-[var(--surface-muted-foreground)]">Renda tributável/ano</dt>
            <dd className="mt-1 font-semibold"><MonetaryValue value={previdencia.renda_tributavel_anual} /></dd>
          </div>
          <div>
            <dt className="text-[var(--surface-muted-foreground)]">Limite PGBL/ano (12%)</dt>
            <dd className="mt-1 font-semibold"><MonetaryValue value={previdencia.limite_pgbl_anual} /></dd>
          </div>
          <div>
            <dt className="text-[var(--surface-muted-foreground)]">Aporte sugerido/mês</dt>
            <dd className="mt-1 font-semibold"><MonetaryValue value={previdencia.aporte_mensal} /></dd>
          </div>
          {previdencia.economia_ir_anual !== undefined && (
            <div>
              <dt className="text-[var(--surface-muted-foreground)]">Economia de IR/ano</dt>
              <dd className="mt-1 font-semibold text-[var(--semantic-gain)]">
                <MonetaryValue value={previdencia.economia_ir_anual} />
              </dd>
            </div>
          )}
        </dl>
        {previdencia.nota && (
          <p className="rounded-md bg-[var(--surface-muted)] p-3 text-xs text-[var(--surface-muted-foreground)]">
            {previdencia.nota}
          </p>
        )}
      </div>
    </ReportCard>
  );
}
