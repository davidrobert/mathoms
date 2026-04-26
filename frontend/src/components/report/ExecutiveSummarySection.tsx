import { HeroKpiGrid } from "./kpi/HeroKpiGrid";
import type { ReportAnalysisData } from "@/lib/api";
import type {
  PatrimonioData,
  RatiosData,
  ReservaEmergenciaData,
} from "@/types/report-analysis";

interface ExecutiveSummarySectionProps {
  data: ReportAnalysisData;
}

/** v2.F.2 — Sumário Executivo (KPIs do hero) entre cover e S1.
 *
 * Container não-numerado, fora da TOC seccional. Paridade com
 * `EXEMPLO_DE_RELATORIO.html:1376` (`<section id="kpis">`). Os 6 KPIs
 * cruzam S1/S2/S7/S10 — não pertencem a nenhuma seção temática isolada.
 */
export function ExecutiveSummarySection({ data }: ExecutiveSummarySectionProps) {
  const patrimonio = data.patrimonio as PatrimonioData | undefined;
  const reserva = data.reserva_emergencia as ReservaEmergenciaData | undefined;
  const ratios = data.ratios as RatiosData | undefined;
  const score = data.score;
  const goals = data.goals as Record<string, unknown> | undefined;

  return (
    <section
      id="sumario-executivo"
      className="scroll-mt-20"
      aria-label="Sumário Executivo — Indicadores-chave"
    >
      <HeroKpiGrid
        patrimonio={patrimonio}
        reserva={reserva}
        ratios={ratios}
        goals={goals}
        score={score}
      />
    </section>
  );
}
