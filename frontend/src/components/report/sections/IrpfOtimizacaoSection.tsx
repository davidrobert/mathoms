"use client";

import { ReportSection } from "../ReportSection";
import { SectionSummary } from "../SectionSummary";
import { IrpfPgblCapacidadeCard } from "../cards";
import { useIrpfKpis } from "../hooks/useIrpfKpis";
import type { ReportAnalysisData } from "@/lib/api";

/** ADR-157 · S_IRPF_OTIMIZACAO — Otimização tributária.
 *
 * Hoje publica apenas o card PGBL (números reais do `IRPFAnalyzer`). Cards
 * "Dependentes Declarados" e "Dedutíveis Subutilizados" foram removidos por
 * publicarem apenas texto explicativo sem dados — o produto Premium não pode
 * mostrar "análise entra em próxima iteração" como conteúdo. Voltam quando
 * `IRPFAnalyzer` emitir `dependentes_count` + `dedutiveis_por_categoria`. */
export function IrpfOtimizacaoSection({ data }: { data: ReportAnalysisData }) {
  const kpis = useIrpfKpis(data);
  if (!kpis) return null;

  const narrativas = data.narrativas as Record<string, unknown> | undefined;

  return (
    <ReportSection id="S_IRPF_OTIMIZACAO" title="Otimização Tributária">
      <SectionSummary narrativas={narrativas} sectionId="S_IRPF_OTIMIZACAO" />
      <IrpfPgblCapacidadeCard kpis={kpis} />
    </ReportSection>
  );
}
