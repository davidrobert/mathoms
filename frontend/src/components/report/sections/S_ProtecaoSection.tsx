"use client";

import type { ReportAnalysisData } from "@/lib/api/reports";
import { ReportSection } from "../ReportSection";
import { SectionSummary } from "../SectionSummary";
import { ProtecaoApolices } from "./SProtecao/ProtecaoApolices";
import { ProtecaoGapQualitativo } from "./SProtecao/ProtecaoGapQualitativo";
import { ProtecaoGapVeiculos } from "./SProtecao/ProtecaoGapVeiculos";
import { ProtecaoKpiHero } from "./SProtecao/ProtecaoKpiHero";
import { readProtecaoPatrimonial } from "../utils/reportContractGuards";

/** S_PROTECAO — 4º pilar AUVP (ADR-240). Renderiza apenas quando workspace
 *  tem apólices ingeridas (`protecao_patrimonial` presente). Subgrupos:
 *  Bens (auto V1) + Pessoas-V2 placeholder + PJ-V2 placeholder. */
export function S_ProtecaoSection({ data }: { data: ReportAnalysisData }) {
  const protecao = readProtecaoPatrimonial(data.protecao_patrimonial);
  if (!protecao) {
    return null;
  }
  return (
    <ReportSection id="S_PROTECAO">
      <SectionSummary data={data} sectionId="S_PROTECAO" />
      <ProtecaoKpiHero data={protecao} />
      <h3 className="text-style-subtitle mt-6">Bens (V1: auto)</h3>
      <ProtecaoGapVeiculos bens={protecao.bens_com_gap_cobertura} />
      <ProtecaoGapQualitativo gaps={protecao.gap_qualitativo} />
      <ProtecaoApolices data={protecao} />
      {/* A40.l7 — o texto anterior AFIRMAVA algo falso: dizia que a S8 "detalha
          cobertura de previdência", e a S8 mostra renda tributável PF, limite de
          12% e dedutibilidade — o lado FISCAL, não o de proteção. Trocar só o
          nome da seção preservaria a mentira. O link text é idêntico ao
          `shortLabel` e ao prefixo do <h2>, para o leitor procurar no índice a
          mesma string que clicou. */}
      <p className="mt-4 text-style-caption text-muted" data-testid="protecao-crosslink-s8">
        A base dedutível de PGBL está em{" "}
        <a href="#S8" className="underline">
          Carga Tributária PJ
        </a>{" "}
        — previdência aparece neste relatório pelo lado fiscal. Coberturas de
        risco embutidas no plano de previdência não entram nesta análise.
      </p>
    </ReportSection>
  );
}
