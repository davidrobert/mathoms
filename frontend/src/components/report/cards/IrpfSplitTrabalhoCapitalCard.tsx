import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import type { CardVariant } from "@/generated/report-layout";
import { parseDecimalString, type IrpfKpis } from "@/types/irpf";

interface IrpfSplitTrabalhoCapitalCardProps {
  kpis: IrpfKpis;
  variant?: CardVariant;
}

interface SplitLegendProps {
  label: string;
  value: number;
  pct: number;
  swatchClass: string;
}

function SplitLegend({ label, value, pct, swatchClass }: SplitLegendProps) {
  return (
    <div>
      <dt className="flex items-center gap-2 text-[var(--surface-muted-foreground)]">
        <span className={`inline-block h-2 w-2 rounded-full ${swatchClass}`} aria-hidden />
        {label}
      </dt>
      <dd className="mt-1">
        <p className="font-mono text-lg font-semibold tabular-nums">
          <MonetaryValue value={value} />
        </p>
        <p className="font-mono text-xs tabular-nums text-[var(--surface-muted-foreground)]">
          {pct.toFixed(1).replace(".", ",")}% do total
        </p>
      </dd>
    </div>
  );
}

/** ADR-157 · S_IRPF_RENDA — Split trabalho × capital (Perini).
 *
 * Trabalho = PJ + PF + 13º. Capital = isentos (lucros, poupança), exclusiva
 * (JCP, aplicações, ganho de capital), exterior. Bar dual com proporção. */
export function IrpfSplitTrabalhoCapitalCard({
  kpis,
  variant = "feature",
}: IrpfSplitTrabalhoCapitalCardProps) {
  const trabalho = parseDecimalString(kpis.split_trabalho_brl) ?? 0;
  const capital = parseDecimalString(kpis.split_capital_brl) ?? 0;
  const total = trabalho + capital;
  const pctTrabalho = total > 0 ? (trabalho / total) * 100 : 0;
  const pctCapital = total > 0 ? (capital / total) * 100 : 0;

  return (
    <ReportCard
      variant={variant}
      size="full"
      title="Renda do Trabalho × Renda do Capital"
    >
      <div className="space-y-4">
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Decomposição da renda familiar entre fonte trabalho (salários, autônomo,
          13º) e fonte capital (lucros, JCP, aplicações, exterior).
        </p>
        {total > 0 && (
          <div
            className="flex h-3 overflow-hidden rounded-full bg-[var(--surface-muted)]"
            role="img"
            aria-label={`Proporção: ${pctTrabalho.toFixed(0)}% trabalho, ${pctCapital.toFixed(0)}% capital`}
          >
            <div className="bg-[var(--brand-primary)]" style={{ width: `${pctTrabalho}%` }} />
            <div className="bg-[var(--semantic-gain)]" style={{ width: `${pctCapital}%` }} />
          </div>
        )}
        <dl className="grid grid-cols-2 gap-4 text-sm">
          <SplitLegend
            label="Trabalho"
            value={trabalho}
            pct={pctTrabalho}
            swatchClass="bg-[var(--brand-primary)]"
          />
          <SplitLegend
            label="Capital"
            value={capital}
            pct={pctCapital}
            swatchClass="bg-[var(--semantic-gain)]"
          />
        </dl>
      </div>
    </ReportCard>
  );
}
