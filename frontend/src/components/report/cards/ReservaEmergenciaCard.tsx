import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import type { CardVariant } from "@/generated/report-layout";
import type { ReservaEmergenciaData } from "@/types/report-analysis";

interface ReservaEmergenciaCardProps {
  reserva: ReservaEmergenciaData | undefined;
  /** Variant vinda do YAML. Default: "warn" (conforme layout S1). */
  variant?: CardVariant;
}

/** F9 · F2.A · S1 — Card "Reserva de Emergência".
 *
 * Mostra cobertura em meses vs metas (6m e 12m) + avaliação qualitativa.
 *
 * Regra de variant (F3.2 refinará): se cobertura < 3 meses, força critical;
 * entre 3 e 6 warn; ≥ 6 success. Respeita override do layout.yaml.
 */
export function ReservaEmergenciaCard({
  reserva,
  variant = "warn",
}: ReservaEmergenciaCardProps) {
  const cobertura = reserva?.cobertura_meses ?? 0;
  const total = reserva?.total_liquida ?? 0;
  const despesasMensais = reserva?.despesas_mensais ?? 0;
  const nivel6 = reserva?.nivel_6_meses ?? 0;
  const nivel12 = reserva?.nivel_12_meses ?? 0;
  const pctRumoA12 = nivel12 > 0 ? Math.min(100, (total / nivel12) * 100) : 0;

  const computedVariant: CardVariant =
    cobertura < 3 ? "critical" : cobertura < 6 ? "warn" : "success";

  return (
    <ReportCard
      variant={variant === "warn" ? computedVariant : variant}
      size="half"
      title="Reserva de Emergência"
    >
      <div className="space-y-4">
        <div>
          <p className="font-mono text-3xl font-semibold tabular-nums text-[var(--surface-foreground)]">
            {cobertura.toFixed(1).replace(".", ",")} meses
          </p>
          <p className="text-sm text-[var(--surface-muted-foreground)]">
            de cobertura • {reserva?.avaliacao_liquidity ?? "—"}
          </p>
        </div>

        <dl className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <dt className="text-[var(--surface-muted-foreground)]">Total líquido</dt>
            <dd>
              <MonetaryValue value={total} />
            </dd>
          </div>
          <div>
            <dt className="text-[var(--surface-muted-foreground)]">Despesas/mês</dt>
            <dd>
              <MonetaryValue value={despesasMensais} />
            </dd>
          </div>
          <div>
            <dt className="text-[var(--surface-muted-foreground)]">Meta 6 meses</dt>
            <dd>
              <MonetaryValue value={nivel6} />
            </dd>
          </div>
          <div>
            <dt className="text-[var(--surface-muted-foreground)]">Meta 12 meses</dt>
            <dd>
              <MonetaryValue value={nivel12} />
            </dd>
          </div>
        </dl>

        <div>
          <div
            className="h-2 rounded-full bg-[var(--surface-muted)]"
            role="progressbar"
            aria-valuenow={pctRumoA12}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Progresso rumo à reserva de 12 meses"
          >
            <div
              className="h-full rounded-full bg-[var(--semantic-gain)] transition-[width]"
              style={{ width: `${pctRumoA12}%` }}
            />
          </div>
          <p className="mt-1 text-xs text-[var(--surface-muted-foreground)]">
            {pctRumoA12.toFixed(0)}% da meta de 12 meses
          </p>
        </div>
      </div>
    </ReportCard>
  );
}
