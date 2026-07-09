"use client";

import { ReportCard } from "../ReportCard";
import { ChartWaterfall } from "./primitives/ChartWaterfall";
import { fmtBRL, fmtCompact } from "./_shared";
import type { PatrimonioData } from "@/types/report-analysis";

interface WaterfallIfChartProps {
  patrimonio: PatrimonioData | undefined;
  goals:
    | {
        if_meta?: number;
        if_pct?: number;
        if_gap?: number;
      }
    | undefined;
  conclusion?: string;
}

/** W5-T02 (v2.E.9) · S1 — Chart "Caminho para a Independência Financeira".
 *
 * Migrado de Recharts (3 barras aterradas) → `ChartWaterfall` (primitives),
 * fechando o resíduo intencional da Onda v2.E (ADR-139, emenda 2026-07-08).
 * "Atual" e "Meta" viram pilares e "Gap" vira floating bar atual→meta —
 * waterfall de verdade, alinhado ao nome do chart. Cores seguem a
 * semântica do primitive (pilares primary, delta positivo accent).
 */
export function WaterfallIfChart({
  patrimonio,
  goals,
  conclusion,
}: WaterfallIfChartProps) {
  // ADR-142 + ADR-215 §6: "Atual" deve casar com o denominador do if_pct.
  // investivel_efetivo == investivel_financeiro quando imoveis_no_if=false
  // (cat2_efetivo zera no calculator), então cobre ambos os casos sem branch.
  const atual =
    patrimonio?.investivel_efetivo ?? patrimonio?.investivel_financeiro ?? 0;
  const meta = goals?.if_meta ?? 0;
  const gap = goals?.if_gap ?? Math.max(0, meta - atual);
  const pct = goals?.if_pct ?? (meta > 0 ? (atual / meta) * 100 : 0);

  if (meta === 0) {
    return (
      <ReportCard variant="neutral" title="Caminho para Independência Financeira">
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Meta de IF não configurada.
        </p>
      </ReportCard>
    );
  }

  return (
    <ReportCard variant="neutral" title="Caminho para Independência Financeira" conclusion={conclusion}>
      <p className="mb-3 text-sm text-[var(--surface-muted-foreground)]">
        Progresso atual:{" "}
        <span className="font-mono font-semibold text-[var(--brand-primary)] tabular-nums">
          {pct.toFixed(1).replace(".", ",")}%
        </span>{" "}
        da meta.
      </p>
      <div className="w-full">
        <ChartWaterfall
          steps={[
            { label: "Atual", value: atual, kind: "start" },
            { label: "Gap", value: gap, kind: "delta" },
            { label: "Meta", value: meta, kind: "end" },
          ]}
          formatValue={fmtBRL}
          formatAxisValue={fmtCompact}
          height={224}
          ariaLabel="Caminho para a independência financeira: patrimônio atual, gap e meta"
        />
      </div>
    </ReportCard>
  );
}
