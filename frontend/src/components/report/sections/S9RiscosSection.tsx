"use client";

import { ShieldOff } from "lucide-react";

import { EmptyState } from "@/components/EmptyState";
import type { ReportAnalysisData } from "@/lib/api";

import {
  AcoesMitigacaoCard,
  CoberturaSegurosCard,
  HeroGapProtecaoCard,
  SucessaoCard,
  type ProtectionBundle,
} from "../cards";
import {
  NarrativeChartCard,
  type MitigationLegendItem,
} from "../charts/NarrativeChartCard";
import { ReportSection } from "../ReportSection";
import { SectionSummary } from "../SectionSummary";
import { deriveChartConclusion } from "../utils/conclusionUtils";
import { S9CoberturaNaoConfirmada } from "./S9CoberturaNaoConfirmada";
import { protectionSectionState } from "./s9ProtectionInputs";

interface MitigationCounts {
  coberto: number;
  parcial: number;
  descoberto: number;
}

function countMitigationStatuses(
  gapAnalysis: ProtectionBundle["gap_analysis"] | undefined,
): MitigationCounts {
  const counts = { coberto: 0, parcial: 0, descoberto: 0 };
  if (!gapAnalysis) return counts;
  for (const value of Object.values(gapAnalysis)) {
    if (value.gap_brl === null || value.gap_brl === undefined) {
      // ADR-395 §D4: `actual_brl` nulo é "não medido". `?? 0` aqui refaria no
      // render a afirmação de zero que o produtor deixou de fazer.
      if ((value.actual_brl ?? 0) > 0) counts.coberto += 1;
    } else if (value.gap_brl > 0) {
      counts.descoberto += 1;
    } else {
      counts.coberto += 1;
    }
  }
  return counts;
}

/** Legenda canônica da 3ª dimensão (cor) do bubble `bubble_riscos`
 * — ADR-192 §D4 (re-enquadramento). Ordem: descoberto → parcial →
 * coberto. Counts injetados quando bundle disponível. */
function buildMitigationLegend(
  bundle: ProtectionBundle | undefined,
): MitigationLegendItem[] {
  const counts = countMitigationStatuses(bundle?.gap_analysis);
  const total = counts.coberto + counts.parcial + counts.descoberto;
  const has = total > 0;
  return [
    { status: "descoberto", label: "Descoberto", count: has ? counts.descoberto : undefined },
    { status: "parcial", label: "Parcial", count: has ? counts.parcial : undefined },
    { status: "coberto", label: "Coberto", count: has ? counts.coberto : undefined },
  ];
}

/** F9 · F2.F · ADR-117 / ADR-192 §D4 (S9-T04) — Seção S9 (Riscos e Proteção).
 *
 * Expandida em T04 para 5 blocos paritários com S10:
 *   - HeroGapProtecaoCard (full, KPI protagonista)
 *   - CoberturaSegurosCard (full, tabela densa)
 *   - SucessaoCard (half) + AcoesMitigacaoCard (half)
 *   - NarrativeChartCard bubble_riscos (full, re-enquadrado: apenas
 *     riscos compliance/sucessório + 3ª dimensão cor = mitigation_status)
 *
 * Empty state total só quando o snapshot não trouxe insumo real
 * (A40.l35). `bubble_riscos.data_state === "empty"` sozinho não esconde
 * a seção — o gráfico pode estar vazio e o bundle ainda ter apólice.
 */
export function S9RiscosSection({ data }: { data: ReportAnalysisData }) {
  const narrativas = data.narrativas as Record<string, unknown> | undefined;
  const charts = narrativas?.charts as Record<string, unknown> | undefined;
  const bundle = data.protection_bundle ?? undefined;
  const sectionState = protectionSectionState(bundle);
  const effectiveDate = (data.data_analise as string | undefined) ?? null;
  const mitigationLegend = buildMitigationLegend(bundle);

  return (
    <ReportSection id="S9">
      {/* ADR-356: fora do estado apurado, o bloco abaixo JÁ é a mensagem da
          seção. Imprimir o `s9` acima dele repetiria a mesma afirmação com
          wording diferente — deduplicar o CTA não bastava. */}
      {sectionState === "apurado" && <SectionSummary data={data} sectionId="S9" />}
      {sectionState === "parcial" && bundle?.documentary_coverage && (
        <S9CoberturaNaoConfirmada documentary={bundle.documentary_coverage} />
      )}
      {sectionState === "nao_apurado" && (
        <div className="md:col-span-2">
          {/* ADR-395 §D3 — ausência declarada NOMEIA o insumo que falta. A copy
              anterior ("sem riscos cadastrados") afirmava algo sobre o
              patrimônio do cliente a partir de uma fonte só. */}
          <EmptyState
            icon={ShieldOff}
            title="Ainda não temos insumo para analisar seus riscos"
            description="Não recebemos apólice nos documentos enviados nem cadastro de proteção — sem uma dessas fontes não há o que medir em cobertura, sucessão ou compliance. Isto não afirma que você está descoberto."
            action={{ href: "/protecao", label: "Cadastrar apólices" }}
          />
        </div>
      )}
      {sectionState === "apurado" && (
        <>
          <HeroGapProtecaoCard bundle={bundle} effectiveDate={effectiveDate} />
          <CoberturaSegurosCard bundle={bundle} effectiveDate={effectiveDate} />
          <SucessaoCard bundle={bundle} effectiveDate={effectiveDate} />
          <AcoesMitigacaoCard bundle={bundle} effectiveDate={effectiveDate} />
          <NarrativeChartCard
            chartId="bubble_riscos"
            title="Mapa de Riscos — Compliance e Sucessório"
            narratives={charts}
            fallbackConclusion={deriveChartConclusion("bubble_riscos", data)}
            mitigationLegend={mitigationLegend}
          />
        </>
      )}
    </ReportSection>
  );
}
