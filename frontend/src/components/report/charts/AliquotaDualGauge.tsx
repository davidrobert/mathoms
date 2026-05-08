"use client";

import { ReportCard } from "../ReportCard";
import { ChartGaugeSemi, useChartTheme } from "./primitives";
import { parseDecimalString, type IrpfKpis } from "@/types/irpf";

interface AliquotaDualGaugeProps {
  kpis: IrpfKpis;
  conclusion?: string;
}

interface GaugePanelProps {
  value: number;
  label: string;
  caption: string;
  fillColor: string;
}

const GAUGE_MAX_PCT = 27.5;

function GaugePanel({ value, label, caption, fillColor }: GaugePanelProps) {
  const display = `${value.toFixed(1).replace(".", ",")}%`;
  return (
    <div className="flex flex-col items-center">
      <ChartGaugeSemi
        value={Math.min(value, GAUGE_MAX_PCT)}
        max={GAUGE_MAX_PCT}
        fillColor={fillColor}
        centerValue={display}
        centerLabel={label}
        height={180}
        ariaLabel={`${label}: ${display}`}
      />
      <p className="mt-2 max-w-[18rem] text-center text-xs leading-relaxed text-[var(--surface-muted-foreground)]">
        {caption}
      </p>
    </div>
  );
}

/** ADR-157 · S_IRPF_RENDA — gauge dual de alíquota efetiva.
 *
 * Esquerda: alíquota sobre rendimento tributável (visão RFB tradicional).
 * Direita: alíquota sobre renda total incluindo isentos/exclusiva (visão
 * Cerbasi/Perini, mais dura, captura JCP/lucros). Os dois números convivem
 * porque dizem coisas diferentes — o relatório não eleva nenhum a "o certo". */
export function AliquotaDualGauge({ kpis, conclusion }: AliquotaDualGaugeProps) {
  const theme = useChartTheme();
  const sobreTributavel = parseDecimalString(kpis.aliquota_sobre_tributavel_pct) ?? 0;
  const sobreTotal = parseDecimalString(kpis.aliquota_sobre_total_pct) ?? 0;

  return (
    <ReportCard
      variant="neutral"
      title="Alíquota Efetiva — RFB e Renda Total"
      conclusion={conclusion}
    >
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <GaugePanel
          value={sobreTributavel}
          label="Sobre tributável"
          caption="Base RFB: IR pago dividido pela renda tributável. Faixa máxima 27,5%."
          fillColor={theme.primary}
        />
        <GaugePanel
          value={sobreTotal}
          label="Sobre total"
          caption="Visão sobre renda total: IR pago dividido pela renda total declarada (incluindo isentos e exclusiva). Tipicamente menor."
          fillColor={theme.accent}
        />
      </div>
    </ReportCard>
  );
}
