import { MonetaryValue } from "../MonetaryValue";
import { formatPercent } from "@/lib/format";
import type { FluxoNaturezaMensalRow } from "@/types/report-analysis";

const NATUREZA_LABELS: Record<FluxoNaturezaMensalRow["natureza"], string> = {
  receita_pj: "PJ",
  receita_clt: "CLT",
  receita_aluguel: "Aluguéis",
  receita_outras: "Outras",
};

const NATUREZA_HINT: Partial<
  Record<FluxoNaturezaMensalRow["natureza"], string>
> = {
  receita_pj: "Pró-labore + lucros",
  receita_outras: "Rendimentos, resgates, FGTS e demais entradas",
};

function NaturezaCell({ row }: { readonly row: FluxoNaturezaMensalRow }) {
  const hint = NATUREZA_HINT[row.natureza];
  return (
    <div data-natureza={row.natureza} className="min-w-0">
      <p className="font-display font-semibold">
        {NATUREZA_LABELS[row.natureza]}
      </p>
      {hint ? (
        <p className="text-xs text-[var(--surface-muted-foreground)]">{hint}</p>
      ) : null}
      <p className="mt-1">
        <MonetaryValue value={row.mensal_media} />
      </p>
      <p className="font-mono tabular-nums text-xs text-[var(--surface-muted-foreground)]">
        {formatPercent(row.participacao_pct, 2)}
      </p>
    </div>
  );
}

/** A40.l44 PR6 — recorte por tipo; ordem e valores vêm do E5. */
export function ReceitasNaturezaStrip({
  rows,
}: {
  readonly rows: readonly FluxoNaturezaMensalRow[];
}) {
  if (rows.length === 0) return null;
  return (
    <div data-testid="receita-natureza-strip">
      <p className="mb-2 text-sm font-display font-semibold">Por tipo</p>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {rows.map((row) => (
          <NaturezaCell key={row.natureza} row={row} />
        ))}
      </div>
    </div>
  );
}
