import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import type { ExposicaoCambialData } from "@/types/report-analysis";

interface ExposicaoCambialCardProps {
  data: ExposicaoCambialData | undefined;
}

const TIER_LABEL: Record<string, string> = {
  verde: "adequado",
  amarelo: "abaixo do recomendado",
  vermelho: "sub-alocado",
  empty: "sem exposição",
};

const TIER_BADGE_CLASS: Record<string, string> = {
  verde: "bg-[var(--semantic-success)]/15 text-[var(--semantic-success)]",
  amarelo: "bg-[var(--semantic-warning)]/15 text-[var(--semantic-warning)]",
  vermelho: "bg-[var(--semantic-danger)]/15 text-[var(--semantic-danger)]",
  empty: "bg-[var(--surface-muted)] text-[var(--surface-muted-foreground)]",
};

/** Bloco G plan/RESIDENCIA_E_USO (co-design 2026-05-18) — Card "Exposição Cambial".
 *
 * Renderiza patrimônio com lastro em moeda estrangeira (caixa USD/EUR +
 * ativos com lastro internacional via ADR-193 bucket "Internacional").
 * Threshold canônico (financial-planner): verde ≥10% · amarelo 5-10% ·
 * vermelho <5%. Denominador: `investivel_financeiro` (Cerbasi/AUVP).
 */
export function ExposicaoCambialCard({ data }: ExposicaoCambialCardProps) {
  if (!data) {
    return null;
  }

  const tier = data.tier;
  const badgeText =
    tier === "empty"
      ? "0% sem exposição"
      : `${data.pct_investivel_financeiro.toFixed(1)}% · ${TIER_LABEL[tier] ?? tier}`;

  return (
    <ReportCard variant="feature" title="Exposição Cambial">
      <div className="space-y-4">
        <header className="flex items-start justify-between gap-4">
          <p className="text-sm text-[var(--surface-muted-foreground)]">
            Patrimônio protegido contra desvalorização do real.
          </p>
          <span
            className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${
              TIER_BADGE_CLASS[tier] ?? TIER_BADGE_CLASS.empty
            }`}
          >
            {badgeText}
          </span>
        </header>

        {tier === "empty" ? (
          <p className="text-sm text-[var(--surface-muted-foreground)]">
            Seu patrimônio está 100% denominado em real. Diversificação cambial reduz risco
            de perda de poder de compra em cenários de desvalorização do real.
          </p>
        ) : (
          <>
            <div>
              <div className="font-mono text-3xl font-bold tabular-nums">
                <MonetaryValue value={data.total_brl} />
              </div>
              <div className="text-sm text-[var(--surface-muted-foreground)]">
                do patrimônio investível financeiro
              </div>
            </div>

            {data.por_moeda.length > 0 && (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--surface-border)] text-left">
                    <th className="pb-2 font-display font-semibold">Moeda</th>
                    <th className="pb-2 text-right font-display font-semibold">
                      Equiv. BRL
                    </th>
                    <th className="pb-2 text-right font-display font-semibold">%</th>
                  </tr>
                </thead>
                <tbody>
                  {data.por_moeda.map((row) => (
                    <tr
                      key={row.moeda}
                      className="border-b border-[var(--surface-border)]/40 last:border-0"
                    >
                      <td className="py-2">{row.moeda}</td>
                      <td className="py-2 text-right">
                        <MonetaryValue value={row.valor_brl} />
                      </td>
                      <td className="py-2 text-right font-mono tabular-nums text-[var(--surface-muted-foreground)]">
                        {row.pct_total_cambial.toFixed(1)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        )}

        <p className="text-xs text-[var(--surface-muted-foreground)]">
          Considera caixa em moeda forte (USD, EUR) + ativos classificados como
          internacional (IVVB, fundos globais). Sugestão de alocação contracíclica:
          ≥10% em moeda forte como proteção de poder de compra.
        </p>
      </div>
    </ReportCard>
  );
}
