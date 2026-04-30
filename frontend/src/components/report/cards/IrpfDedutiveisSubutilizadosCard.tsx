import { ReportCard } from "../ReportCard";
import type { CardVariant } from "@/generated/report-layout";
import type { IrpfKpis } from "@/types/irpf";

interface IrpfDedutiveisSubutilizadosCardProps {
  kpis: IrpfKpis;
  variant?: CardVariant;
}

/** ADR-157 · S_IRPF_OTIMIZACAO — dedutíveis subutilizados (placeholder).
 *
 * Saúde, educação, livro caixa e pensão alimentícia entram como dedutíveis no
 * modelo completo. O KPI base ainda não detalha esse breakdown; o card mantém
 * o slot e textualiza o tema sem fabricar valores. Follow-up: ampliar o shape
 * `irpf_kpis` com `dedutiveis_por_categoria` e plotar comparação vs. teto. */
export function IrpfDedutiveisSubutilizadosCard({
  variant = "warn",
}: IrpfDedutiveisSubutilizadosCardProps) {
  return (
    <ReportCard variant={variant} size="full" title="Dedutíveis Subutilizados">
      <div className="space-y-3 text-sm text-[var(--surface-muted-foreground)]">
        <p>
          Saúde (sem teto), educação (com teto anual por dependente), pensão
          alimentícia judicial e livro caixa são dedutíveis no modelo completo.
          Comparar o que foi declarado com o teto permitido revela espaço para
          economia tributária no ano seguinte.
        </p>
        <p className="text-xs leading-relaxed">
          A análise detalhada por categoria entra em uma próxima iteração do
          relatório. No modelo simplificado o desconto único de 20% absorve
          todos os dedutíveis — verificar regime ano a ano.
        </p>
      </div>
    </ReportCard>
  );
}
