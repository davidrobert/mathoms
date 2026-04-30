"use client";

import { ReportSection } from "../ReportSection";
import { SectionSummary } from "../SectionSummary";
import {
  IrpfRendaAnualCard,
  IrpfIrPagoCard,
  IrpfSplitTrabalhoCapitalCard,
} from "../cards";
import { RendaEvolucaoChart } from "../charts/RendaEvolucaoChart";
import { AliquotaDualGauge } from "../charts/AliquotaDualGauge";
import { useIrpfKpis } from "../hooks/useIrpfKpis";
import type { ReportAnalysisData } from "@/lib/api";

/** ADR-157 · S_IRPF_RENDA — Renda anual e impostos.
 *
 * Degrada graciosamente: workspaces sem `irpf_kpis` no E5 retornam null
 * (a seção inteira não é montada — sem placeholder vazio). */
export function IrpfRendaSection({ data }: { data: ReportAnalysisData }) {
  const kpis = useIrpfKpis(data);
  if (!kpis) return null;

  const narrativas = data.narrativas as Record<string, unknown> | undefined;

  return (
    <ReportSection id="S_IRPF_RENDA" title="Renda Anual e Impostos">
      <SectionSummary narrativas={narrativas} sectionId="S_IRPF_RENDA" />
      <div className="md:col-span-2">
        <RendaEvolucaoChart kpis={kpis} />
      </div>
      <div className="md:col-span-2">
        <AliquotaDualGauge kpis={kpis} />
      </div>
      <IrpfRendaAnualCard kpis={kpis} />
      <IrpfIrPagoCard kpis={kpis} />
      <IrpfSplitTrabalhoCapitalCard kpis={kpis} />
    </ReportSection>
  );
}
