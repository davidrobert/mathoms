import { KpiCard } from "../ui/Kpi";
import { MonetaryValue } from "../MonetaryValue";
import { formatFullBRL } from "@/lib/format";
import type {
  PatrimonioData,
  RatiosData,
  ReservaEmergenciaData,
  ScoreData,
} from "@/types/report-analysis";
import type { KpiTone } from "../ui/Kpi";

interface HeroKpiGridProps {
  patrimonio: PatrimonioData | undefined;
  reserva: ReservaEmergenciaData | undefined;
  ratios: RatiosData | undefined;
  goals: Record<string, unknown> | undefined;
  score: ScoreData | undefined;
}

/** v2.F.1 · S1 — Hero de 6 KPIs em 2 linhas (3-3 em xl).
 *
 * Linha 1 — onde estou: Líquido · **Investível (HERO)** · Reserva (semáforo)
 * Linha 2 — para onde vou: Taxa Poupança · **IF (HERO composto)** · Score
 *
 * Custo de Vida e Renda Mensal vivem em S2 Fluxo de Caixa — aqui aparecem
 * apenas como contexto inline em sub-labels (Reserva em meses, etc.).
 */
export function HeroKpiGrid({
  patrimonio,
  reserva,
  ratios,
  goals,
  score,
}: HeroKpiGridProps) {
  return (
    <div className="mb-10 grid gap-4 grid-cols-1 sm:grid-cols-2 xl:grid-cols-3">
      <PatrimonioLiquidoKpi patrimonio={patrimonio} />
      <PatrimonioInvestivelKpi patrimonio={patrimonio} />
      <ReservaKpi reserva={reserva} />
      <TaxaPoupancaKpi ratios={ratios} />
      <IndependenciaKpi goals={goals} />
      <ScoreKpi score={score} />
    </div>
  );
}

function PatrimonioLiquidoKpi({ patrimonio }: { patrimonio: PatrimonioData | undefined }) {
  const liquido = patrimonio?.liquido;
  const bruto = patrimonio?.bruto;
  return (
    <KpiCard
      label="Patrimônio Líquido"
      value={formatCompactBRL(liquido)}
      sub={
        bruto != null ? (
          <>
            Bruto:{" "}
            <MonetaryValue
              value={bruto}
              compact
              title={formatFullBRL(bruto)}
            />
          </>
        ) : undefined
      }
    />
  );
}

function PatrimonioInvestivelKpi({ patrimonio }: { patrimonio: PatrimonioData | undefined }) {
  const investivel = patrimonio?.investivel;
  const liquido = patrimonio?.liquido;
  const pctLiquido =
    investivel != null && liquido != null && liquido > 0
      ? (investivel / liquido) * 100
      : undefined;
  return (
    <KpiCard
      hero
      accent="primary"
      tone="blue"
      label="Patrimônio Investível"
      value={formatCompactBRL(investivel)}
      sub={
        pctLiquido != null
          ? `${pctLiquido.toFixed(1).replace(".", ",")}% do líquido`
          : patrimonio?.fonte_investimentos
            ? `Fonte: ${patrimonio.fonte_investimentos}`
            : undefined
      }
    />
  );
}

function ReservaKpi({ reserva }: { reserva: ReservaEmergenciaData | undefined }) {
  const meses = reserva?.cobertura_meses ?? reserva?.composicao_liquida?.cobertura_meses;
  const tone = reservaTone(meses);
  return (
    <KpiCard
      label="Reserva de Emergência"
      tone={tone}
      value={meses != null ? `${meses.toFixed(1).replace(".", ",")} meses` : "—"}
      sub={
        meses != null
          ? `Meta 6–12m · ${reservaLabel(meses)}`
          : "Sem dados"
      }
    />
  );
}

function reservaTone(meses: number | undefined): KpiTone {
  if (meses == null) return "default";
  if (meses < 3) return "red";
  if (meses < 6) return "warning";
  return "green";
}

function reservaLabel(meses: number): string {
  if (meses < 3) return "crítica";
  if (meses < 6) return "atenção";
  if (meses < 12) return "adequada";
  return "excelente";
}

function TaxaPoupancaKpi({ ratios }: { ratios: RatiosData | undefined }) {
  const recorrente = ratios?.taxa_poupanca_recorrente_pct;
  const total = ratios?.taxa_poupanca_total_pct;
  return (
    <KpiCard
      label="Taxa de Poupança"
      value={
        recorrente != null
          ? `${recorrente.toFixed(1).replace(".", ",")}%`
          : "—"
      }
      sub={
        total != null
          ? `Recorrente · Total: ${total.toFixed(1).replace(".", ",")}%`
          : "Recorrente"
      }
    />
  );
}

function IndependenciaKpi({ goals }: { goals: Record<string, unknown> | undefined }) {
  const ifPct = numericField(goals, "if_pct");
  const ifGap = numericField(goals, "if_gap");
  const anoIf = numericField(goals, "ano_if");
  const prazoAnos =
    anoIf != null ? Math.max(0, anoIf - new Date().getFullYear()) : undefined;
  const progressValue = ifPct != null ? Math.max(0, Math.min(1, ifPct / 100)) : undefined;
  const valueText = ifPct != null ? `${ifPct.toFixed(0)}%` : "—";
  return (
    <KpiCard
      hero
      accent="primary"
      tone="blue"
      label="Independência Financeira"
      value={valueText}
      progress={progressValue != null ? { value: progressValue, tone: "blue" } : undefined}
      sub={
        <div className="flex flex-col gap-0.5">
          <span>
            Prazo:{" "}
            <strong>
              {prazoAnos != null ? `${prazoAnos} anos` : "—"}
              {anoIf != null ? ` (${anoIf})` : ""}
            </strong>
          </span>
          <span style={{ color: "var(--brand-danger)" }}>
            Gap:{" "}
            {ifGap != null ? (
              <MonetaryValue
                value={-Math.abs(ifGap)}
                compact
                signed
                title={formatFullBRL(ifGap)}
              />
            ) : (
              "—"
            )}
          </span>
        </div>
      }
    />
  );
}

function ScoreKpi({ score }: { score: ScoreData | undefined }) {
  const tone: KpiTone = score ? scoreTone(score.valor, score.max) : "default";
  return (
    <KpiCard
      label="Score Financeiro"
      tone={tone}
      value={
        score
          ? `${score.valor.toFixed(1).replace(".", ",")} / ${score.max}`
          : "—"
      }
      sub={score?.classificacao ?? (score ? scoreLabel(score.valor, score.max) : undefined)}
    />
  );
}

function scoreTone(valor: number, max: number): KpiTone {
  if (max <= 0) return "default";
  const ratio = valor / max;
  if (ratio < 0.4) return "red";
  if (ratio < 0.6) return "warning";
  return "green";
}

function scoreLabel(valor: number, max: number): string {
  if (max <= 0) return "—";
  const ratio = valor / max;
  if (ratio < 0.4) return "Atenção";
  if (ratio < 0.6) return "Bom";
  return "Ótimo";
}

function formatCompactBRL(value: number | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

function numericField(
  obj: Record<string, unknown> | undefined,
  key: string,
): number | undefined {
  if (!obj) return undefined;
  const v = obj[key];
  if (typeof v === "number" && !Number.isNaN(v)) return v;
  if (typeof v === "string") {
    const n = Number(v);
    return Number.isFinite(n) ? n : undefined;
  }
  return undefined;
}
