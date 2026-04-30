import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import type { CardVariant } from "@/generated/report-layout";
import { parseDecimalString, type IrpfKpis } from "@/types/irpf";

interface IrpfIrPagoCardProps {
  kpis: IrpfKpis;
  variant?: CardVariant;
}

function formatPct(s: string): string {
  const n = parseDecimalString(s);
  if (n === null) return "—";
  return `${n.toFixed(2).replace(".", ",")}%`;
}

/** ADR-157 · S_IRPF_RENDA — IR pago no ano + alíquota efetiva (RFB e Cerbasi).
 *
 * "Sobre tributável" = base RFB (renda tributável). "Sobre total" = sob renda
 * total incluindo isentos/exclusiva (visão Cerbasi/Perini, mais dura). G0 fechou
 * a copy: a tabela mostra os dois lados sem indicar qual é "o certo". */
export function IrpfIrPagoCard({ kpis, variant = "feature" }: IrpfIrPagoCardProps) {
  const ir = parseDecimalString(kpis.ir_pago_total_brl);

  return (
    <ReportCard variant={variant} size="half" title="IR Pago">
      <div className="space-y-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-[var(--surface-muted-foreground)]">
            Total recolhido · {kpis.ano_base}
          </p>
          <p className="mt-1 font-mono text-2xl font-semibold tabular-nums">
            <MonetaryValue value={ir} />
          </p>
        </div>
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <dt className="text-[var(--surface-muted-foreground)]">Sobre tributável</dt>
            <dd className="mt-1 font-mono font-semibold tabular-nums">
              {formatPct(kpis.aliquota_sobre_tributavel_pct)}
            </dd>
          </div>
          <div>
            <dt className="text-[var(--surface-muted-foreground)]">Sobre total</dt>
            <dd className="mt-1 font-mono font-semibold tabular-nums">
              {formatPct(kpis.aliquota_sobre_total_pct)}
            </dd>
          </div>
        </dl>
      </div>
    </ReportCard>
  );
}
