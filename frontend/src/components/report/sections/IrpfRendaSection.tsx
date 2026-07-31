"use client";

import { ReportSection } from "../ReportSection";
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
 * (a seção inteira não é montada — sem placeholder vazio).
 *
 * A40.l4: sem parágrafo de abertura. O `<SectionSummary>` daqui era render site
 * MORTO nas três camadas da ADR-355 — medido: a seção não está em
 * `SUPPORTED_SECTION_IDS` (LLM), tem `summary_source: null` (E5.N não produz
 * narrativa fiscal-IRPF) e não tem entrada em `SECTION_SUMMARIES`
 * (`conclusionUtils.ts`), então `resolveSectionSummary` devolvia `null` sempre.
 * `summary: false` no layout mantém a regra 6 do gate estático honesta. Dar
 * texto de abertura a esta seção é decisão de copy, não desta lane. */
export function IrpfRendaSection({ data }: { data: ReportAnalysisData }) {
  const kpis = useIrpfKpis(data);
  if (!kpis) return null;

  return (
    <ReportSection id="S_IRPF_RENDA" title="Renda Anual e Impostos">
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
