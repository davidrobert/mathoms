"use client";

import { ReportCard } from "../ReportCard";
import { ReportSection } from "../ReportSection";
import { SectionSummary } from "../SectionSummary";
import { SuggestionCalloutInline } from "./SuggestionCallout";
import { PrevidenciaPgblCard, type PrevidenciaPgblData } from "../cards";
import { NarrativeChartCard } from "../charts/NarrativeChartCard";
import { MonetaryValue } from "../MonetaryValue";
import { AcumuladoresBanner } from "../AcumuladoresBanner";
import { DefasagemWarningBanner } from "../DefasagemWarningBanner";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { formatCurrency } from "@/lib/format";
import { deriveChartConclusion } from "../utils/conclusionUtils";
import { EmptyState } from "@/components/EmptyState";
import { FileText, Wallet } from "lucide-react";
import type { IFMonteCarloData, PassiveIncomeData, ReportAnalysisData } from "@/lib/api";
import { IFConeConeChart } from "../charts/IFConeConeChart";
import { useIrpfKpis } from "../hooks/useIrpfKpis";
import {
  derivePrimaryYear,
  getPgblCardStrategy,
  isInformativeMode,
} from "@/lib/irpf/pgbl-card-strategy";

const PHASE_INDEPENDENCIA = 95;
const PHASE_ACUMULACAO = 50;
const ACUMULADORES_THRESHOLD = 40;
const DEFASAGEM_INFO_THRESHOLD = 6;
const DEFASAGEM_WARNING_THRESHOLD = 15;
const APROXIMACAO_YIELD_RATIO = 0.7;

/** F9 · F2.E — Seção S7 (Independência Financeira). */
export function S7IndependenciaSection({
  data,
  workspaceId,
}: {
  data: ReportAnalysisData;
  workspaceId?: string;
}) {
  const narrativas = data.narrativas as Record<string, unknown> | undefined;
  const charts = narrativas?.charts as Record<string, unknown> | undefined;
  const previdencia = data.previdencia_pgbl as unknown as PrevidenciaPgblData | undefined;
  const goals = data.goals as Record<string, unknown> | undefined;
  const passiveIncome = data.passive_income;
  const monteCarloIF = data.if_monte_carlo;
  const irpfKpis = useIrpfKpis(data);
  const labels = (data.fluxo_caixa as { receita_despesa_mensal_detalhado?: { labels?: string[] } } | undefined)
    ?.receita_despesa_mensal_detalhado?.labels;
  const pgblStrategy = getPgblCardStrategy(irpfKpis, derivePrimaryYear(labels));

  return (
    <ReportSection id="S7" title="Independência Financeira — Projeção de Longo Prazo">
      <SectionSummary narrativas={narrativas} sectionId="S7" />
      {workspaceId && (
        <SuggestionCalloutInline sectionId="S7" workspaceId={workspaceId} />
      )}
      <NarrativeChartCard
        chartId="projecao_3cenarios"
        title="Projeção Patrimonial — 3 Cenários"
        narratives={charts}
        fallbackConclusion={deriveChartConclusion("projecao_3cenarios", data)}
      />
      <NarrativeChartCard
        chartId="renda_passiva"
        title="Renda Passiva — Progresso até a Meta"
        narratives={charts}
        fallbackConclusion={deriveChartConclusion("renda_passiva", data)}
      />

      {goals && (
        <div className="md:col-span-2 grid grid-cols-2 gap-4 md:grid-cols-4">
          <Stat label="Meta IF" value={<MonetaryValue value={goals.if_meta as number | undefined} compact />} />
          <Stat label="Progresso" value={`${((goals.if_pct as number) ?? 0).toFixed(1)}%`} />
          <Stat label="Ano projetado" value={String(goals.ano_if ?? "—")} />
          <Stat label="Gap" value={<MonetaryValue value={goals.if_gap as number | undefined} compact />} />
        </div>
      )}

      <IFMonteCarloBlock
        monteCarloIF={monteCarloIF}
        metaIf={goals?.if_meta as number | undefined}
      />

      <PassiveIncomeBlock
        passiveIncome={passiveIncome}
        progressoIfPct={(goals?.if_pct as number | undefined) ?? 0}
        trsMetaPct={(goals?.trs_pct as number | undefined) ?? 5.0}
      />

      <div className={isInformativeMode(pgblStrategy.mode) ? "md:col-span-1" : "md:col-span-2"}>
        <PrevidenciaPgblCard
          previdencia={previdencia}
          mode={pgblStrategy.mode}
          anoBase={pgblStrategy.anoBase ?? undefined}
        />
      </div>
    </ReportSection>
  );
}

function Stat({
  label,
  value,
  sublabel,
  tone = "neutral",
}: {
  label: React.ReactNode;
  value: React.ReactNode;
  sublabel?: React.ReactNode;
  tone?: "neutral" | "positive" | "warning";
}) {
  const toneClass =
    tone === "warning"
      ? "border-[var(--semantic-warning)]"
      : tone === "positive"
        ? "border-[var(--semantic-success)]"
        : "border-[var(--surface-border)]";
  return (
    <div className={`rounded-[var(--radius-card)] border ${toneClass} bg-[var(--surface-card)] p-4`}>
      <p className="text-xs uppercase tracking-wider text-[var(--surface-muted-foreground)]">{label}</p>
      <p className="mt-1 text-lg font-semibold">{value}</p>
      {sublabel && (
        <div className="mt-1 text-xs text-[var(--surface-muted-foreground)]">{sublabel}</div>
      )}
    </div>
  );
}

/** N3 — Bloco do cone de probabilidade Monte Carlo (P10/P50/P90). */
function IFMonteCarloBlock({
  monteCarloIF,
  metaIf,
}: {
  monteCarloIF: IFMonteCarloData | undefined;
  metaIf: number | undefined;
}) {
  if (!monteCarloIF) return null;

  if (!monteCarloIF.exibir_cone) {
    if (!monteCarloIF.motivo_sem_cone) return null;
    return (
      <p className="text-xs text-[var(--surface-muted-foreground)] md:col-span-2 italic">
        {monteCarloIF.motivo_sem_cone}
      </p>
    );
  }

  return (
    <ReportCard
      variant="feature"
      size="full"
      title="Cone de probabilidade — IF (Monte Carlo)"
    >
      <p className="mb-3 text-xs text-[var(--surface-muted-foreground)]">
        Projeção estocástica com volatilidade de{" "}
        {(monteCarloIF.sigma_usado * 100).toFixed(0)}% a.a.
        {monteCarloIF.aporte_mensal_usado && monteCarloIF.aporte_mensal_usado > 0 ? (
          <>
            {" "}considerando aporte mensal de{" "}
            <strong>{formatCurrency(monteCarloIF.aporte_mensal_usado)}</strong>{" "}
            mantido em termos reais.
          </>
        ) : (
          <>
            {" "}sem aporte mensal — só o patrimônio atual compondo.
          </>
        )}{" "}
        Probabilidade de atingir IF até a idade {monteCarloIF.idade_meta_usada}:{" "}
        <strong>{formatProbability(monteCarloIF.prob_if_ate_idade_meta)}</strong>
      </p>
      <IFConeConeChart
        caminhoP10={monteCarloIF.caminho_p10}
        caminhoP50={monteCarloIF.caminho_p50}
        caminhoP90={monteCarloIF.caminho_p90}
        metaIf={metaIf}
        data-testid="s7-if-cone-chart"
      />
    </ReportCard>
  );
}

/** ADR-237 — formata probabilidade para evitar "0%" enganoso quando
 * prob ∈ (0, 1%), e "100%" quando prob ∈ (99%, 100%). */
export function formatProbability(prob: number): string {
  if (prob <= 0) return "0%";
  if (prob >= 1) return "100%";
  if (prob < 0.01) return "<1%";
  if (prob > 0.99) return ">99%";
  return `${(prob * 100).toFixed(0)}%`;
}

/** A8.3 — Bloco de KPIs de TRS efetiva (4 cards) + caption + 2 banners + empty states. */
function PassiveIncomeBlock({
  passiveIncome,
  progressoIfPct,
  trsMetaPct,
}: {
  passiveIncome: PassiveIncomeData | undefined;
  progressoIfPct: number;
  trsMetaPct: number;
}) {
  if (!passiveIncome) return null;
  if (passiveIncome.status === "sem_irpf") return <SemIrpfEmptyState />;
  if (passiveIncome.status === "gerador_zero") return <GeradorZeroEmptyState />;
  return (
    <PassiveIncomeOkBlock
      data={passiveIncome}
      progressoIfPct={progressoIfPct}
      trsMetaPct={trsMetaPct}
    />
  );
}

function PassiveIncomeOkBlock({
  data,
  progressoIfPct,
  trsMetaPct,
}: {
  data: PassiveIncomeData;
  progressoIfPct: number;
  trsMetaPct: number;
}) {
  const acumuladoresPct = data.acumuladores_pct_gerador;
  const defasagem = data.defasagem_meses ?? 0;
  return (
    <>
      <div className="md:col-span-2 grid grid-cols-1 gap-4 md:grid-cols-4">
        <RendaPassivaStat data={data} />
        <PatrimonioGeradorStat data={data} />
        <TrsEfetivaStat
          data={data}
          progressoIfPct={progressoIfPct}
          trsMetaPct={trsMetaPct}
        />
        <AcumuladoresStat acumuladoresPct={acumuladoresPct} />
      </div>

      {progressoIfPct < PHASE_ACUMULACAO && (
        <p className="text-xs text-[var(--surface-muted-foreground)] mt-2">
          Carteira em acumulação — yield baixo é esperado nesta fase. Retorno total
          inclui valorização, não só dividendo.
        </p>
      )}

      {acumuladoresPct > ACUMULADORES_THRESHOLD && (
        <AcumuladoresBanner pct={acumuladoresPct} />
      )}
      {defasagem >= DEFASAGEM_WARNING_THRESHOLD && (
        <DefasagemWarningBanner ano={data.ano_referencia_irpf} meses={defasagem} />
      )}
    </>
  );
}

function RendaPassivaStat({ data }: { data: PassiveIncomeData }) {
  return (
    <Stat
      label="Renda passiva"
      value={
        <span className="inline-flex items-baseline gap-1">
          <MonetaryValue value={data.renda_passiva_mensal_brl} compact />
          <span className="text-xs text-[var(--surface-muted-foreground)]">/mês</span>
        </span>
      }
      sublabel={
        <span className="text-sm">
          {formatCurrency(data.renda_passiva_anual_brl)} / ano
        </span>
      }
    />
  );
}

function PatrimonioGeradorStat({ data }: { data: PassiveIncomeData }) {
  return (
    <Stat
      label="Patrimônio investido"
      value={<MonetaryValue value={data.patrimonio_gerador_brl} compact />}
    />
  );
}

function TrsEfetivaStat({
  data,
  progressoIfPct,
  trsMetaPct,
}: {
  data: PassiveIncomeData;
  progressoIfPct: number;
  trsMetaPct: number;
}) {
  const tone = trsTone(data.trs_efetiva_pct, trsMetaPct, progressoIfPct);
  const defasagem = data.defasagem_meses ?? 0;
  return (
    <Stat
      label={
        <span className="inline-flex items-center gap-1">
          TRS efetiva
          <InfoTooltip
            ariaLabel="Sobre TRS efetiva"
            content="Yield observado vs. meta de retirada sustentável (alvo 5% — padrão de mercado; piso conservador 4% — Trinity Study)."
          />
        </span>
      }
      value={`${data.trs_efetiva_pct.toFixed(1)}%`}
      tone={tone}
      sublabel={
        <>
          Meta {trsMetaPct.toFixed(1).replace(".", ",")}%
          {defasagem >= DEFASAGEM_INFO_THRESHOLD && (
            <span className="block text-xs text-[var(--surface-muted-foreground)] mt-1">
              IRPF {data.ano_referencia_irpf} · {defasagem}m de defasagem
            </span>
          )}
        </>
      }
    />
  );
}

function AcumuladoresStat({ acumuladoresPct }: { acumuladoresPct: number }) {
  const isHigh = acumuladoresPct > ACUMULADORES_THRESHOLD;
  const isZero = acumuladoresPct === 0;
  return (
    <Stat
      label="Em acumuladores"
      value={
        <span
          className={isZero ? "text-[var(--surface-muted-foreground)]" : undefined}
        >
          {`${acumuladoresPct.toFixed(0)}%`}
        </span>
      }
      tone={isHigh ? "warning" : "neutral"}
      sublabel={
        isZero
          ? "Sem ETFs/fundos acumuladores"
          : isHigh
            ? (
              <span className="text-[var(--semantic-warning)]">
                &gt;40% subestima TRS
              </span>
            )
            : "ETFs/fundos sem distribuição"
      }
    />
  );
}

function SemIrpfEmptyState() {
  return (
    <EmptyState
      icon={FileText}
      title="Importe seu IRPF para calcular a TRS efetiva"
      description="Sem a declaração, exibimos só a projeção. Com IRPF importado, calculamos sua renda passiva real (dividendos, JCP, aluguéis) sobre a carteira atual. Aceita PDF da Receita ou .DEC."
      action={{ href: "/documents", label: "Importar IRPF" }}
    />
  );
}

function GeradorZeroEmptyState() {
  return (
    <EmptyState
      icon={Wallet}
      title="TRS efetiva começa quando há patrimônio investido"
      description="Ainda não identificamos ativos geradores de renda na sua carteira. Esta métrica passa a fazer sentido com os primeiros aportes — até lá, foque na meta de aporte mensal e na reserva de emergência."
    />
  );
}

/** A8.3 — Tom condicionado à fase do plano (Perini · D4). */
export function trsTone(
  efetiva: number,
  meta: number,
  progresso: number,
): "neutral" | "positive" | "warning" {
  if (progresso < PHASE_ACUMULACAO) return "neutral";
  if (progresso < PHASE_INDEPENDENCIA) {
    return efetiva >= meta * APROXIMACAO_YIELD_RATIO ? "neutral" : "warning";
  }
  return efetiva >= meta ? "positive" : "warning";
}
