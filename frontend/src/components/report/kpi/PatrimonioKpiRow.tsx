import { cn } from "@/lib/cn";
import { MonetaryValue } from "../MonetaryValue";
import { getScoreColorVar, getScoreLabel } from "../utils/scoreUtils";
import type {
  PatrimonioData,
  RatiosData,
  ScoreData,
} from "@/types/report-analysis";

interface PatrimonioKpiRowProps {
  patrimonio: PatrimonioData | undefined;
  ratios: RatiosData | undefined;
  score: ScoreData | undefined;
}

/** F9 · F2.A · S1 — Linha de 4 KPIs no topo do relatório.
 *
 * Antigamente era uma faixa no `.cover-hero` do report_template.html.
 * Nativo: grid 2/4 colunas, tipografia editorial, monetário com font-mono.
 */
export function PatrimonioKpiRow({
  patrimonio,
  ratios,
  score,
}: PatrimonioKpiRowProps) {
  const taxaPoupanca = ratios?.taxa_poupanca_recorrente_pct;

  return (
    <div className="mb-10 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <Kpi
        label="Patrimônio Líquido"
        value={<MonetaryValue value={patrimonio?.liquido} />}
      />
      <Kpi
        label="Investível"
        value={<MonetaryValue value={patrimonio?.investivel} />}
        hint={
          patrimonio?.fonte_investimentos
            ? `Fonte: ${patrimonio.fonte_investimentos}`
            : undefined
        }
      />
      <Kpi
        label="Taxa de Poupança"
        value={
          <span className="font-mono tabular-nums">
            {taxaPoupanca !== undefined
              ? `${taxaPoupanca.toFixed(1).replace(".", ",")}%`
              : "—"}
          </span>
        }
        hint="Recorrente"
      />
      <Kpi
        label="Score Financeiro"
        value={
          <span
            className="font-mono tabular-nums"
            style={score ? { color: getScoreColorVar(score.valor, score.max) } : undefined}
          >
            {score ? `${score.valor.toFixed(1).replace(".", ",")}/${score.max}` : "—"}
          </span>
        }
        hint={score ? (score.classificacao ?? getScoreLabel(score.valor, score.max)) : undefined}
      />
    </div>
  );
}

function Kpi({
  label,
  value,
  hint,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-[var(--radius-card)] border border-[var(--surface-border)] bg-[var(--surface-card)] p-4",
        "shadow-[var(--shadow-sm)]",
      )}
    >
      <p className="text-xs uppercase tracking-wider text-[var(--surface-muted-foreground)]">
        {label}
      </p>
      <p className="mt-2 text-2xl font-semibold leading-tight text-[var(--surface-foreground)]">
        {value}
      </p>
      {hint && (
        <p className="mt-1 text-xs text-[var(--surface-muted-foreground)]">
          {hint}
        </p>
      )}
    </div>
  );
}
