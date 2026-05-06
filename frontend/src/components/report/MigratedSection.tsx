import type { ReportAnalysisData } from "@/lib/api";
import { S1PatrimonioSection } from "./sections/S1PatrimonioSection";
import { S2FluxoCaixaSection } from "./sections/S2FluxoCaixaSection";
import { S3InvestimentosSection } from "./sections/S3InvestimentosSection";
import { S4RealEstateSection } from "./sections/S4RealEstateSection";
import { S7IndependenciaSection } from "./sections/S7IndependenciaSection";
import { S8PrevidenciaSection } from "./sections/S8PrevidenciaSection";
import { IrpfRendaSection } from "./sections/IrpfRendaSection";
import { IrpfOtimizacaoSection } from "./sections/IrpfOtimizacaoSection";
import { S9RiscosSection } from "./sections/S9RiscosSection";
import { S10SinteseSection } from "./sections/S10SinteseSection";
import { PlanoDeAcaoSection } from "./sections/PlanoDeAcao";
import { ApendiceASection } from "./sections/ApendiceASection";
import {
  ApendiceBSection,
  ApendiceCSection,
  ApendiceDSection,
  ApendiceESection,
} from "./sections/ApendicesSections";

/** Conjunto de IDs de seções com renderer concreto. Mantém o shell desacoplado
 *  do dispatcher. ADR-157 inclui as seções IRPF (degrada gracioso quando
 *  workspaces não têm `irpf_kpis`). Modo USA (U1-U4) removido em ADR-168. */
export const MIGRATED_SECTIONS: ReadonlySet<string> = new Set([
  "S1", "S2", "S3", "S4", "S7", "S8", "S9", "S10",
  "S_IRPF_RENDA", "S_IRPF_OTIMIZACAO",
  "plano_de_acao",
  "APP_A", "APP_B", "APP_C", "APP_D", "APP_E",
]);

interface MigratedSectionProps {
  sectionId: string;
  data: ReportAnalysisData;
  workspaceId: string;
}

/** Dispatcher das seções migradas. Cada caso aponta para um componente
 *  concreto em `sections/`. Default: `null` (seção segue como stub). */
export function MigratedSection({
  sectionId,
  data,
  workspaceId,
}: MigratedSectionProps) {
  switch (sectionId) {
    case "S1":
      return <S1PatrimonioSection data={data} />;
    case "S2":
      return <S2FluxoCaixaSection data={data} workspaceId={workspaceId} />;
    case "S3":
      return <S3InvestimentosSection data={data} />;
    case "S4":
      return <S4RealEstateSection data={data} />;
    case "S7":
      return <S7IndependenciaSection data={data} workspaceId={workspaceId} />;
    case "S8":
      return <S8PrevidenciaSection data={data} />;
    case "S_IRPF_RENDA":
      return <IrpfRendaSection data={data} />;
    case "S_IRPF_OTIMIZACAO":
      return <IrpfOtimizacaoSection data={data} />;
    case "S9":
      return <S9RiscosSection data={data} />;
    case "S10":
      return <S10SinteseSection data={data} />;
    case "plano_de_acao":
      return <PlanoDeAcaoSection workspaceId={workspaceId} />;
    case "APP_A":
      return <ApendiceASection data={data} />;
    case "APP_B":
      return <ApendiceBSection data={data} />;
    case "APP_C":
      return <ApendiceCSection data={data} />;
    case "APP_D":
      return <ApendiceDSection data={data} />;
    case "APP_E":
      return <ApendiceESection data={data} />;
    default:
      return null;
  }
}
