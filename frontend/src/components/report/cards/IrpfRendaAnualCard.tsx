import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import type { CardVariant } from "@/generated/report-layout";
import { parseDecimalString, type IrpfKpis } from "@/types/irpf";

interface IrpfRendaAnualCardProps {
  kpis: IrpfKpis;
  variant?: CardVariant;
}

/** ADR-157 · S_IRPF_RENDA — Renda anual familiar (bruta + líquida). */
export function IrpfRendaAnualCard({ kpis, variant = "feature" }: IrpfRendaAnualCardProps) {
  const bruta = parseDecimalString(kpis.renda_anual_familiar_brl);
  const liquida = parseDecimalString(kpis.renda_liquida_familiar_brl);

  return (
    <ReportCard variant={variant} size="half" title="Renda Anual Familiar">
      <div className="space-y-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-[var(--surface-muted-foreground)]">
            Bruta · {kpis.ano_base}
          </p>
          <p className="mt-1 font-mono text-2xl font-semibold tabular-nums">
            <MonetaryValue value={bruta} />
          </p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-[var(--surface-muted-foreground)]">
            Líquida (após IR, INSS e pensão)
          </p>
          <p className="mt-1 font-mono text-xl font-semibold tabular-nums text-[var(--semantic-gain)]">
            <MonetaryValue value={liquida} />
          </p>
        </div>
      </div>
    </ReportCard>
  );
}
