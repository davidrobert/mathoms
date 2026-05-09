import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import type { CardVariant } from "@/generated/report-layout";
import { parseDecimalString, type IrpfKpis } from "@/types/irpf";

interface IrpfPgblCapacidadeCardProps {
  kpis: IrpfKpis;
  variant?: CardVariant;
}

/** ADR-157 · S_IRPF_OTIMIZACAO — capacidade PGBL não usada.
 *
 * Mostra o teto dedutível (12% da renda tributável) ainda disponível no ano-base.
 * Workspaces no modelo simplificado: o analyzer já retorna 0 (PGBL não deduz).
 * Copy aprovada por G0: é informação de capacidade, não recomendação automática
 * — a contratação de PGBL exige análise de regime tributário, INSS, perfil. */
export function IrpfPgblCapacidadeCard({
  kpis,
  variant = "warn",
}: IrpfPgblCapacidadeCardProps) {
  const capacidade = parseDecimalString(kpis.pgbl_capacidade_dedutivel_brl) ?? 0;
  const semCapacidade = capacidade <= 0;
  const resolvedVariant: CardVariant = semCapacidade ? "neutral" : variant;

  return (
    <ReportCard
      variant={resolvedVariant}
      size="half"
      title="Capacidade PGBL"
    >
      <div className="space-y-3">
        {semCapacidade ? (
          <>
            <MonetaryValue value={0} size="kpi" />
            <p className="text-sm text-[var(--surface-muted-foreground)]">
              Sem capacidade dedutível adicional em {kpis.ano_base} — modelo
              simplificado ou aporte já no teto de 12% da renda tributável.
            </p>
          </>
        ) : (
          <>
            <div>
              <p className="text-xs uppercase tracking-wide text-[var(--surface-muted-foreground)]">
                Espaço dedutível remanescente · {kpis.ano_base}
              </p>
              <MonetaryValue value={capacidade} size="kpi" className="mt-1" />
            </div>
            <p className="text-xs leading-relaxed text-[var(--surface-muted-foreground)]">
              Diferença entre 12% da renda tributável e os aportes PGBL já
              registrados. <strong>Não é recomendação:</strong> contratar PGBL exige
              análise de regime de tributação, contribuição ao INSS e perfil
              previdenciário.
            </p>
          </>
        )}
      </div>
    </ReportCard>
  );
}
