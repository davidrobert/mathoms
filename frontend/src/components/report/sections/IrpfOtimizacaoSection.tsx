"use client";

import { ReportSection } from "../ReportSection";
import {
  IrpfDedutiveisAplicadosCard,
  IrpfDependentesCard,
  IrpfPgblCapacidadeCard,
} from "../cards";
import { useIrpfKpis } from "../hooks/useIrpfKpis";
import type { ReportAnalysisData } from "@/lib/api";
import type { IrpfKpis } from "@/types/irpf";

/** ADR-157 + ADR-189 + ADR-194 · S_IRPF_OTIMIZACAO — Otimização tributária.
 *
 * 3 cards: PGBL Capacidade (half, 4 estados — ADR-189) + Dependentes
 * Declarados (half, factual — ADR-194 §6.1) + Dedutíveis Aplicados por
 * Categoria (full, 4 categorias sparse — ADR-194 §6.2). Cards "Dependentes"
 * e "Dedutíveis" foram reativados em A12 (ADR-194) após removidos em 2026-05
 * por serem prose-only. Guards escondem cards vazios sem regredir o PGBL.
 *
 * A40.l4: sem parágrafo de abertura, mesma razão medida da `IrpfRendaSection` —
 * render site morto nas três camadas da ADR-355 (`summary: false` no layout). */
export function IrpfOtimizacaoSection({ data }: { data: ReportAnalysisData }) {
  const kpis = useIrpfKpis(data);
  if (!kpis) return null;

  return (
    <ReportSection id="S_IRPF_OTIMIZACAO" title="Otimização Tributária">
      <IrpfPgblCapacidadeCard kpis={kpis} />
      {shouldRenderDependentes(kpis) && (
        <IrpfDependentesCard
          dependentes={kpis.dependentes!}
          anoBase={kpis.ano_base}
        />
      )}
      {shouldRenderDedutiveis(kpis) && (
        <IrpfDedutiveisAplicadosCard
          dedutiveis={kpis.dedutiveis_aplicados!}
          anoBase={kpis.ano_base}
          pgblStatus={kpis.pgbl_status}
        />
      )}
    </ReportSection>
  );
}

function shouldRenderDependentes(kpis: IrpfKpis): boolean {
  return kpis.dependentes !== undefined && kpis.dependentes.count > 0;
}

function shouldRenderDedutiveis(kpis: IrpfKpis): boolean {
  const dedutiveis = kpis.dedutiveis_aplicados;
  if (!dedutiveis) return false;
  return Object.keys(dedutiveis).length > 0;
}
