"use client";

import { ReportSection } from "../ReportSection";
import { SectionSummary } from "../SectionSummary";
import {
  IrpfPgblCapacidadeCard,
  IrpfDependentesCard,
  IrpfDedutiveisSubutilizadosCard,
} from "../cards";
import { useIrpfKpis } from "../hooks/useIrpfKpis";
import type { ReportAnalysisData } from "@/lib/api";

/** ADR-157 · S_IRPF_OTIMIZACAO — Otimização tributária.
 *
 * Espaço PGBL não usado, dependentes declarados, dedutíveis subutilizados.
 * Copy aprovada por G0: nenhum card vira recomendação automática. */
export function IrpfOtimizacaoSection({ data }: { data: ReportAnalysisData }) {
  const kpis = useIrpfKpis(data);
  if (!kpis) return null;

  const narrativas = data.narrativas as Record<string, unknown> | undefined;

  return (
    <ReportSection id="S_IRPF_OTIMIZACAO" title="Otimização Tributária">
      <SectionSummary narrativas={narrativas} sectionId="S_IRPF_OTIMIZACAO" />
      <IrpfPgblCapacidadeCard kpis={kpis} />
      <IrpfDependentesCard kpis={kpis} />
      <IrpfDedutiveisSubutilizadosCard kpis={kpis} />
    </ReportSection>
  );
}
