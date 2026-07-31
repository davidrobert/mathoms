import Link from "next/link";
import { KpiCard } from "../ui/Kpi";
import { MonetaryValue } from "../MonetaryValue";
import {
  formatJanelaTooltip,
  janelaBadgeLabel,
  type JanelaRotulo,
} from "../utils/janelaLabel";
import { resolveTaxaPoupanca } from "../utils/fluxoJanela";
import { formatFullBRL } from "@/lib/format";
import type {
  PatrimonioData,
  RatiosData,
  ReservaEmergenciaData,
  ScoreData,
} from "@/types/report-analysis";
import type { KpiTone } from "../ui/Kpi";

const INVESTIVEL_TOOLTIP =
  "Patrimônio Investível: ativos financeiros (investimentos do titular e cônjuge) + caixa em moeda estrangeira. Não inclui residência, veículos nem imóveis não-geradores.";

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
  const financeiro = patrimonio?.investivel_financeiro;
  const efetivo = patrimonio?.investivel_efetivo;
  const geradores = patrimonio?.imoveis_geradores ?? 0;
  const liquido = patrimonio?.liquido;
  const toggleOn = patrimonio?.imoveis_no_if === true;
  const pctLiquido =
    financeiro != null && liquido != null && liquido > 0
      ? (financeiro / liquido) * 100
      : undefined;

  return (
    <KpiCard
      hero
      accent="primary"
      tone="blue"
      label="Patrimônio Investível"
      title={INVESTIVEL_TOOLTIP}
      value={formatCompactBRL(financeiro)}
      sub={
        <InvestivelSubline
          financeiro={financeiro}
          efetivo={efetivo}
          geradores={geradores}
          toggleOn={toggleOn}
          pctLiquido={pctLiquido}
          fonte={patrimonio?.fonte_investimentos}
        />
      }
    />
  );
}

interface InvestivelSublineProps {
  financeiro: number | undefined;
  efetivo: number | undefined;
  geradores: number;
  toggleOn: boolean;
  pctLiquido: number | undefined;
  fonte: string | undefined;
}

function InvestivelSubline({
  financeiro,
  efetivo,
  geradores,
  toggleOn,
  pctLiquido,
  fonte,
}: InvestivelSublineProps) {
  // ADR-142 + ADR-215 §6 + financial-planner (2026-05-20): sub-linha tem 3
  // estados quando toggle on; toggle off mostra contexto neutro.
  if (financeiro == null) {
    return fonte ? <>Fonte: {fonte}</> : null;
  }

  const pctLine =
    pctLiquido != null
      ? `${pctLiquido.toFixed(1).replace(".", ",")}% do líquido`
      : fonte
        ? `Fonte: ${fonte}`
        : null;

  if (!toggleOn) {
    return (
      <div className="flex flex-col gap-0.5">
        {pctLine ? <span>{pctLine}</span> : null}
        <span>Imóveis fora do cálculo de IF</span>
      </div>
    );
  }

  if (geradores > 0 && efetivo != null && efetivo > financeiro) {
    return (
      <div className="flex flex-col gap-0.5">
        {pctLine ? <span>{pctLine}</span> : null}
        <span>
          + <MonetaryValue value={geradores} compact title={formatFullBRL(geradores)} /> em
          imóveis de renda · total efetivo{" "}
          <MonetaryValue value={efetivo} compact title={formatFullBRL(efetivo)} />
        </span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-0.5">
      {pctLine ? <span>{pctLine}</span> : null}
      <span>
        Sem imóveis de renda classificados ·{" "}
        <Link
          href="/config?tab=members"
          style={{ color: "var(--brand-primary)", textDecoration: "underline" }}
        >
          classificar
        </Link>
      </span>
    </div>
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
          ? `${reservaMetaLabel(reserva)} · ${reservaQuality(reserva, meses)}`
          : "Sem dados"
      }
    />
  );
}

/** A28.l9/l1 (PR 787) — alvo dinâmico por perfil de renda (CLT 6 · mista 12 ·
 * PJ-dominante 18); payload antigo sem `meses_alvo` cai no range genérico. */
function reservaMetaLabel(reserva: ReservaEmergenciaData | undefined): string {
  const alvo = reserva?.meses_alvo;
  if (alvo != null && alvo > 0) return `Meta ${alvo}m (perfil de renda)`;
  return "Meta 6–12m";
}

/** Avaliação do payload E5 (fonte de verdade pós-A28.l1) com fallback local. */
function reservaQuality(
  reserva: ReservaEmergenciaData | undefined,
  meses: number,
): string {
  const avaliacao = reserva?.avaliacao_liquidity;
  if (typeof avaliacao === "string" && avaliacao.length > 0) {
    return avaliacao.toLowerCase();
  }
  return reservaLabel(meses);
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

/** ADR-306 D2 + §Emenda A40.l3 — o rótulo da base é **texto impresso**, não
 * tooltip: tooltip é `title=` nativo, não sai no PDF, e o PDF é o artefato que
 * a família guarda. O tooltip fica como complemento ("média mensal calculada
 * sobre …"), nunca como único portador da base.
 *
 * O par (percentual, base) vem de `resolveTaxaPoupanca` justamente para o
 * componente não conseguir imprimir um sem o outro — o defeito medido era ler
 * `ratios.janela_referencia` ("2026-01 a 2026-01", string de PERÍODO) como se
 * fosse vocabulário de janela. */
function TaxaPoupancaKpi({ ratios }: { ratios: RatiosData | undefined }) {
  const taxa = resolveTaxaPoupanca(ratios);
  const recorrente = taxa?.recorrentePct;
  const total = taxa?.totalPct;
  return (
    <KpiCard
      label="Taxa de Poupança"
      title={formatJanelaTooltip(taxa?.rotulo ?? null) ?? undefined}
      value={recorrente != null ? `${recorrente.toFixed(1).replace(".", ",")}%` : "—"}
      sub={<TaxaPoupancaSub total={total} rotulo={taxa?.rotulo ?? null} />}
    />
  );
}

/** Sub-linha do card, dentro do próprio `KpiCard`. Nada de wrapper em volta do
 * card: `<span style={{display:"block"}}>` virava o grid item e o card parava de
 * esticar (134px medidos num item de 171px), além de produzir `span > div`. */
function TaxaPoupancaSub({
  total,
  rotulo,
}: {
  readonly total: number | undefined;
  readonly rotulo: JanelaRotulo | null;
}) {
  const badge = janelaBadgeLabel(rotulo);
  return (
    <>
      {total != null
        ? `Recorrente · Total: ${total.toFixed(1).replace(".", ",")}%`
        : "Recorrente"}
      {badge && (
        <span data-janela-badge style={JANELA_BADGE_STYLE}>
          {badge}
        </span>
      )}
    </>
  );
}

const JANELA_BADGE_STYLE = {
  display: "block",
  marginTop: 2,
  fontSize: "var(--report-font-size-xs, 11px)",
  textTransform: "none",
  letterSpacing: "normal",
  color: "var(--surface-muted-foreground)",
} as const;

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
