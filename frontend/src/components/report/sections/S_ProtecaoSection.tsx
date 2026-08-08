"use client";

import type { ReportAnalysisData } from "@/lib/api/reports";
import { ReportSection } from "../ReportSection";
import { SectionSummary } from "../SectionSummary";
import { ProtecaoApolices } from "./SProtecao/ProtecaoApolices";
import { ProtecaoGapQualitativo } from "./SProtecao/ProtecaoGapQualitativo";
import { ProtecaoGapVeiculos } from "./SProtecao/ProtecaoGapVeiculos";
import { ProtecaoKpiHero } from "./SProtecao/ProtecaoKpiHero";

/** S_PROTECAO — 4º pilar AUVP (ADR-240). Renderiza apenas quando workspace
 *  tem apólices ingeridas (`protecao_patrimonial` presente). Subgrupos:
 *  Bens (auto V1) + Pessoas-V2 placeholder + PJ-V2 placeholder. */
export function S_ProtecaoSection({ data }: { data: ReportAnalysisData }) {
  const protecao = data.protecao_patrimonial ?? null;
  if (protecao === null) {
    return null;
  }
  return (
    <ReportSection id="S_PROTECAO" title="Seguros — Cobertura Contratada">
      <SectionSummary data={data} sectionId="S_PROTECAO" />
      <ProtecaoKpiHero data={protecao} />
      <h3 className="text-style-subtitle mt-6">Bens (V1: auto)</h3>
      <ProtecaoGapVeiculos bens={protecao.bens_com_gap_cobertura} />
      <ProtecaoGapQualitativo gaps={protecao.gap_qualitativo} />
      <ProtecaoApolices data={protecao} />
      <p className="mt-4 text-style-caption text-muted" data-testid="protecao-crosslink-s8">
        Cobertura de previdência (componente de proteção) está detalhada em{" "}
        <a href="#S8" className="underline">
          S8 Previdência
        </a>
        .
      </p>
    </ReportSection>
  );
}
