/** Sprint A16 L2 P5 (ADR-236 §D5) — Steps verticais da cascata fiscal
 * (receita bruta → lucros distribuídos) + linha de carga tributária total.
 *
 * Co-design product-designer + financial-planner (2026-05-21): `<dl>` vertical
 * > waterfall (densidade do card); carga total é linha final da cascata, não
 * KPI hero.
 */
import type { CascataPayload } from "@/lib/api";
import { MonetaryValue } from "../MonetaryValue";

export function CascataLayers({ cascata }: { cascata: CascataPayload }) {
  return (
    <div className="border-l-2 border-[var(--surface-border)] pl-4">
      <LayersList cascata={cascata} />
      <CargaTotalRow cargaPct={cascata.carga_total_pct} />
    </div>
  );
}

function LayersList({ cascata }: { cascata: CascataPayload }) {
  const tributosLabel = labelTributosFederais(cascata.regime);
  const tributosPct = pctOfReceita(cascata.tributos_federais, cascata.receita_bruta);
  return (
    <dl className="space-y-2 text-sm">
      <Layer label="Receita bruta PJ (12m)" value={cascata.receita_bruta} />
      <Layer
        label={`− ${tributosLabel}`}
        value={cascata.tributos_federais}
        subtle={tributosPct ? `${tributosPct} efetivo` : undefined}
      />
      {cascata.iss_total > 0 && (
        <Layer label="− ISS destacado" value={cascata.iss_total} />
      )}
      <Layer label="= Lucro contábil PJ" value={cascata.lucro_contabil_pj} strong />
      <Layer label="− Pró-labore bruto" value={cascata.pro_labore_bruto} />
      {cascata.inss_patronal > 0 && (
        <Layer label="− INSS patronal (20%)" value={cascata.inss_patronal} />
      )}
      <Layer
        label="− INSS empregado + IRRF"
        value={cascata.inss_empregado + cascata.irrf_pro_labore}
      />
      <Layer
        label="= Lucros distribuídos (isentos)"
        value={cascata.lucros_distribuidos}
        strong
      />
    </dl>
  );
}

function CargaTotalRow({ cargaPct }: { cargaPct: number }) {
  const pct = (cargaPct * 100).toFixed(1).replace(".", ",");
  return (
    <div
      className="mt-3 flex items-baseline justify-between gap-2 border-t-2 border-[var(--surface-border)] pt-3"
      aria-label={`Carga tributária total estimada em ${pct} por cento da receita`}
    >
      <span className="text-sm font-display font-semibold text-[var(--surface-foreground)]">
        Carga tributária total
      </span>
      <span className="font-mono text-base font-semibold tabular-nums text-[var(--brand-primary)]">
        {pct}%
      </span>
    </div>
  );
}

function Layer({
  label,
  value,
  subtle,
  strong,
}: {
  label: string;
  value: number;
  subtle?: string;
  strong?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <dt className={strong ? "font-semibold text-[var(--surface-foreground)]" : "text-[var(--surface-muted-foreground)]"}>
        {label}
      </dt>
      <dd className={strong ? "font-semibold" : ""}>
        <MonetaryValue value={value} fractionDigits={0} />
        {subtle && (
          <span className="ml-2 text-xs text-[var(--surface-muted-foreground)]">({subtle})</span>
        )}
      </dd>
    </div>
  );
}

function labelTributosFederais(regime: CascataPayload["regime"]): string {
  if (regime === "simples") return "DAS Simples Nacional";
  if (regime === "lucro_presumido") return "PIS + COFINS + IRPJ + CSLL";
  if (regime === "mei") return "DAS-MEI (R$ 79,90/mês)";
  return "Tributos federais";
}

function pctOfReceita(parte: number, receita: number): string | null {
  if (!receita || receita <= 0) return null;
  return `${((parte / receita) * 100).toFixed(1).replace(".", ",")}%`;
}
