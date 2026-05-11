import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import type { CardVariant } from "@/generated/report-layout";
import { parseDecimalString, type IrpfKpis, type PgblStatus } from "@/types/irpf";

interface IrpfPgblCapacidadeCardProps {
  kpis: IrpfKpis;
  /** Variante default por estado (ADR-189 §D5) é resolvida internamente —
   * prop fica como override opcional para futuras lanes (threshold AUVP). */
  variant?: CardVariant;
}

const VARIANT_BY_STATUS: Record<PgblStatus, CardVariant> = {
  capacidade_disponivel: "info",
  modelo_simplificado: "neutral",
  no_teto: "feature",
  sem_renda_tributavel: "neutral",
};

const SUBTITLE_BY_STATUS: Record<PgblStatus, string> = {
  capacidade_disponivel: "Espaço dedutível remanescente",
  modelo_simplificado: "Não se aplica",
  no_teto: "Teto dedutível atingido",
  sem_renda_tributavel: "Não se aplica",
};

/** ADR-157 / ADR-189 · S_IRPF_OTIMIZACAO — diagnóstico PGBL tipificado.
 *
 * Switch sobre `kpis.pgbl_status` em 4 estados (copy literal de ADR-189 §4,
 * congelada por G0 financial-planner em 2026-05-11). Disclaimer "Não é
 * recomendação" fica restrito a `capacidade_disponivel`; `R$ 0,00` só no
 * `no_teto` (zero monetário real); estados `modelo_simplificado` e
 * `sem_renda_tributavel` rendem "—" (métrica não aplicável). */
export function IrpfPgblCapacidadeCard({
  kpis,
  variant,
}: IrpfPgblCapacidadeCardProps) {
  const status = kpis.pgbl_status;
  const resolvedVariant: CardVariant = variant ?? VARIANT_BY_STATUS[status];
  const anoBase = kpis.ano_base;
  const aportado = parseDecimalString(kpis.pgbl_aportado_brl) ?? 0;
  const teto = parseDecimalString(kpis.pgbl_teto_brl) ?? 0;
  const capacidade = parseDecimalString(kpis.pgbl_capacidade_dedutivel_brl) ?? 0;

  return (
    <ReportCard variant={resolvedVariant} size="half" title="Capacidade PGBL">
      <div className="space-y-3">
        <p className="text-xs uppercase tracking-wide text-[var(--surface-muted-foreground)]">
          {SUBTITLE_BY_STATUS[status]} · {anoBase}
        </p>

        {status === "capacidade_disponivel" && (
          <>
            <p className="mt-1 font-mono text-2xl font-semibold tabular-nums">
              <MonetaryValue value={capacidade} />
            </p>
            <p className="text-sm leading-relaxed text-[var(--surface-muted-foreground)]">
              Você aportou{" "}
              <strong>
                <MonetaryValue value={aportado} />
              </strong>{" "}
              dos{" "}
              <strong>
                <MonetaryValue value={teto} />
              </strong>{" "}
              dedutíveis em {anoBase} (12% da renda tributável).{" "}
              <strong>Não é recomendação:</strong> contratar PGBL exige
              análise de tabela regressiva vs. progressiva, horizonte de
              resgate, taxa de administração e contribuição ao INSS.
            </p>
          </>
        )}

        {status === "modelo_simplificado" && (
          <>
            <p className="mt-1 font-mono text-2xl font-semibold tabular-nums text-[var(--surface-muted-foreground)]">
              —
            </p>
            <p className="text-sm leading-relaxed text-[var(--surface-muted-foreground)]">
              Você declarou pelo modelo simplificado em {anoBase} — neste
              regime, a Receita já aplica um desconto fixo sobre os
              rendimentos tributáveis (limitado a teto anual), e
              contribuições a PGBL não geram dedução adicional. A capacidade
              de 12% só vale no modelo completo.
            </p>
          </>
        )}

        {status === "no_teto" && (
          <>
            <p className="mt-1 font-mono text-2xl font-semibold tabular-nums">
              <MonetaryValue value={0} />
            </p>
            <p className="text-sm leading-relaxed text-[var(--surface-muted-foreground)]">
              Você aportou{" "}
              <strong>
                <MonetaryValue value={aportado} />
              </strong>{" "}
              em {anoBase}, esgotando os 12% dedutíveis da renda tributável
              (
              <strong>
                <MonetaryValue value={teto} />
              </strong>
              ). Não há capacidade dedutível remanescente em {anoBase}.
            </p>
          </>
        )}

        {status === "sem_renda_tributavel" && (
          <>
            <p className="mt-1 font-mono text-2xl font-semibold tabular-nums text-[var(--surface-muted-foreground)]">
              —
            </p>
            <p className="text-sm leading-relaxed text-[var(--surface-muted-foreground)]">
              Em {anoBase}, sua declaração registrou apenas rendimentos
              isentos ou de tributação exclusiva. PGBL deduz da renda
              tributável — sem ela, a métrica não se aplica neste ano.
            </p>
          </>
        )}
      </div>
    </ReportCard>
  );
}
