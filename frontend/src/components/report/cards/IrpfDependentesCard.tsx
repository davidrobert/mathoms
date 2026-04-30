import { ReportCard } from "../ReportCard";
import type { CardVariant } from "@/generated/report-layout";
import type { IrpfKpis } from "@/types/irpf";

interface IrpfDependentesCardProps {
  kpis: IrpfKpis;
  variant?: CardVariant;
}

/** ADR-157 · S_IRPF_OTIMIZACAO — status de dependentes (placeholder informativo).
 *
 * O `IRPFAnalyzer` expõe `dependentes_validos(ano)` mas o KPI ainda não emite
 * a lista no E5; este card permanece como espaço reservado seguindo o padrão
 * S8 (PGBL) e será preenchido em follow-up quando o shape for ampliado. G0
 * vetou recomendação automática de "adicionar cônjuge como dependente" — toca
 * status fiscal real e exige avaliação caso-a-caso. */
export function IrpfDependentesCard({ variant = "feature" }: IrpfDependentesCardProps) {
  return (
    <ReportCard variant={variant} size="half" title="Dependentes Declarados">
      <p className="text-sm text-[var(--surface-muted-foreground)]">
        Os dependentes presentes na declaração reduzem a base de cálculo
        anualmente. Avaliar inclusão exige checagem de renda do dependente,
        comprovação de relação e impacto fiscal real — análise caso-a-caso.
      </p>
    </ReportCard>
  );
}
