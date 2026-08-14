"use client";

import { ReportCard } from "../ReportCard";
import { ReportSection } from "../ReportSection";
import { SectionSummary } from "../SectionSummary";
import { SuggestionCalloutInline } from "./SuggestionCallout";
import { RecalibracaoMcNote } from "./RecalibracaoMcNote";
import { Stat } from "./S7Stat";
import { NarrativeChartCard } from "../charts/NarrativeChartCard";
import { MonetaryValue } from "../MonetaryValue";
import { AcumuladoresBanner } from "../AcumuladoresBanner";
import { DefasagemWarningBanner } from "../DefasagemWarningBanner";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { formatCurrency } from "@/lib/format";
import { deriveChartConclusion } from "../utils/conclusionUtils";
import { EmptyState } from "@/components/EmptyState";
import { AlertTriangle, FileText, Info, Wallet } from "lucide-react";
import type {
  IFMonteCarloData,
  PassiveIncomeData,
  PremissasEconomicasData,
  ReportAnalysisData,
} from "@/lib/api";
import { Alert } from "../ui/Alert";
import { formatProbability } from "../utils/probabilidade";
import {
  computePremissasDegrade,
  hasIfStats,
} from "../utils/dataQualitySignals";
import { IFConeConeChart } from "../charts/IFConeConeChart";
import { useIrpfKpis } from "../hooks/useIrpfKpis";
import { derivePrimaryYear } from "@/lib/irpf/irpf-period-match";
import { PgblLocationNote } from "./S7PgblLocationNote";

const PHASE_ACUMULACAO = 50;
const ACUMULADORES_THRESHOLD = 40;
const DEFASAGEM_INFO_THRESHOLD = 6;
const DEFASAGEM_WARNING_THRESHOLD = 15;

interface S7IndependenciaSectionProps {
  data: ReportAnalysisData;
  workspaceId?: string;
  reportId?: string;
}

/** F9 · F2.E — Seção S7 (Independência Financeira). */
export function S7IndependenciaSection({
  data,
  workspaceId,
  reportId,
}: S7IndependenciaSectionProps) {
  const narrativas = data.narrativas as Record<string, unknown> | undefined;
  const charts = narrativas?.charts as Record<string, unknown> | undefined;
  const goals = data.goals as Record<string, unknown> | undefined;
  const passiveIncome = data.passive_income;
  const monteCarloIF = data.if_monte_carlo;
  const irpfKpis = useIrpfKpis(data);
  const labels = (data.fluxo_caixa as { receita_despesa_mensal_detalhado?: { labels?: string[] } } | undefined)
    ?.receita_despesa_mensal_detalhado?.labels;
  const primaryYear = derivePrimaryYear(labels);

  return (
    <ReportSection id="S7">
      <SectionSummary data={data} sectionId="S7" />
      {workspaceId && (
        <SuggestionCalloutInline
          sectionId="S7"
          workspaceId={workspaceId}
          reportId={reportId}
        />
      )}
      <RecalibracaoMcNote nota={data.recalibracao_mc ?? null} />
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

      {hasIfStats(goals) && (
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
        premissas={data.premissas_economicas}
      />

      <PassiveIncomeBlock
        passiveIncome={passiveIncome}
        progressoIfPct={(goals?.if_pct as number | undefined) ?? 0}
      />

      <PgblLocationNote irpfKpis={irpfKpis} primaryYear={primaryYear} />
    </ReportSection>
  );
}

/** N3 — Bloco do cone de probabilidade Monte Carlo (P10/P50/P90). */
// A40.l25 — `sigma_procedencia` é emitido desde #1338 e não tinha leitor; sem a
// ressalva, a legenda afirma a volatilidade como se fosse medida da carteira.
// Não usa `PremissasFallbackAlert`: âmbar é degradação de dado e acusaria 100%
// dos relatórios — constante não-calibrada é default declarado, não degradação.
function IFMonteCarloBlock({
  monteCarloIF,
  metaIf,
  premissas,
}: {
  monteCarloIF: IFMonteCarloData | undefined;
  metaIf: number | undefined;
  premissas: PremissasEconomicasData | undefined;
}) {
  if (!monteCarloIF) return null;

  if (!monteCarloIF.exibir_cone) {
    if (!monteCarloIF.motivo_sem_cone) return null;
    return (
      <p
        role="note"
        aria-label="Motivo da ausência do cone de probabilidade"
        className="flex items-start gap-1.5 text-xs text-[var(--surface-muted-foreground)] md:col-span-2"
      >
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        <span>{monteCarloIF.motivo_sem_cone}</span>
      </p>
    );
  }

  return (
    <ReportCard
      variant="feature"
      size="full"
      title="Cone de probabilidade — IF (Monte Carlo)"
    >
      <PremissasFallbackAlert premissas={premissas} />
      <p className="mb-3 text-xs text-[var(--surface-muted-foreground)]">
        Projeção estocástica com volatilidade de{" "}
        {(monteCarloIF.sigma_usado * 100).toFixed(0)}% a.a.
        {monteCarloIF.sigma_procedencia === "fallback_codigo" && (
          <> (padrão do modelo, não calibrada à sua carteira)</>
        )}
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
        )}
        {/* ADR-369 D2 — a data é da família, não nossa: a legenda nomeia o
            prazo declarado e o ano que ele fixa. Sem prazo declarado a cláusula
            some (o `motivo` vive no payload); publicar "0%" seria correto e
            inútil. */}
        {monteCarloIF.prob_if_ate_prazo_declarado != null &&
          monteCarloIF.prazo_declarado_anos != null && (
            <>
              {" "}
              Probabilidade de atingir IF dentro dos{" "}
              {monteCarloIF.prazo_declarado_anos} anos que você declarou
              {monteCarloIF.ano_alvo_declarado != null && (
                <> (até {monteCarloIF.ano_alvo_declarado})</>
              )}
              :{" "}
              <strong>
                {formatProbability(monteCarloIF.prob_if_ate_prazo_declarado)}
              </strong>
              {monteCarloIF.prazo_declarado_truncado === true && (
                <>
                  {" "}
                  — piso, porque a simulação cobre{" "}
                  {monteCarloIF.horizonte_simulado_anos ?? 40} anos e o prazo
                  declarado é maior
                </>
              )}
            </>
          )}
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

/** A28.l9 — ressalva obrigatória: nunca renderizar probabilidade precisa
 * sobre premissas de mercado em fallback (`parcial`/`indisponivel`) sem
 * `<Alert>` adjacente acima do cone. */
function PremissasFallbackAlert({
  premissas,
}: {
  premissas: PremissasEconomicasData | undefined;
}) {
  const degrade = computePremissasDegrade(premissas);
  if (!degrade) return null;
  return (
    <div className="mb-3" data-testid="s7-premissas-fallback-alert">
      <Alert
        severity="warning"
        icon={<AlertTriangle className="h-4 w-4" aria-hidden="true" />}
      >
        <p>
          Projeção baseada em premissas de mercado padrão, não calibradas à sua
          carteira ({degrade.classesIndisponiveis}/{degrade.classesTotal} classes sem
          premissa vigente) — trate as probabilidades como referência, não como
          previsão.
        </p>
      </Alert>
    </div>
  );
}


/** A8.3 — Bloco de KPIs de TRS efetiva (4 cards) + caption + 2 banners + empty states. */
function PassiveIncomeBlock({
  passiveIncome,
  progressoIfPct,
}: {
  passiveIncome: PassiveIncomeData | undefined;
  progressoIfPct: number;
}) {
  if (!passiveIncome) return null;
  if (passiveIncome.status === "sem_irpf") return <SemIrpfEmptyState />;
  if (passiveIncome.status === "gerador_zero") return <GeradorZeroEmptyState />;
  return (
    <PassiveIncomeOkBlock data={passiveIncome} progressoIfPct={progressoIfPct} />
  );
}

function PassiveIncomeOkBlock({
  data,
  progressoIfPct,
}: {
  data: PassiveIncomeData;
  progressoIfPct: number;
}) {
  const acumuladoresPct = data.acumuladores_pct_gerador;
  const defasagem = data.defasagem_meses ?? 0;
  return (
    <>
      <div className="md:col-span-2 grid grid-cols-1 gap-4 md:grid-cols-4">
        <RendaPassivaStat data={data} />
        <PatrimonioGeradorStat data={data} />
        <TrsEfetivaStat data={data} />
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
      label={
        <span className="inline-flex items-center gap-1">
          Renda passiva observada
          <InfoTooltip
            ariaLabel="Sobre renda passiva observada"
            content="Renda efetivamente recebida no ano-base do IRPF (dividendos de carteira, JCP, aplicações, aluguéis, exterior). Difere da renda passiva estimada pela regra de retirada exibida na projeção de IF."
          />
        </span>
      }
      value={
        <span className="inline-flex items-baseline gap-1">
          <MonetaryValue value={data.renda_passiva_mensal_brl} compact />
          <span className="text-xs text-[var(--surface-muted-foreground)]">/mês</span>
        </span>
      }
      sublabel={
        <span className="text-sm">
          {formatCurrency(data.renda_passiva_anual_brl)} / ano
          {data.ano_referencia_irpf !== null && ` · IRPF ${data.ano_referencia_irpf}`}
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

/**
 * ADR-191 §Emenda 2026-08-14 (A40.l47): não existe yield-alvo no produto. O único
 * percentual que a família configura é `goals.trs_pct`, que é taxa de **saque**
 * (goal.if.v2 §inputs; `if_meta = renda × 12 ÷ trs_pct`) — compará-lo com o yield
 * observado é a promoção que o RV4-13 denuncia. A TRS efetiva sustenta-se sozinha.
 * Exportado para a guarda asserir a copy — `TooltipContent` só monta no open, então
 * o DOM não a expõe.
 */
export const TRS_EFETIVA_TOOLTIP =
  "Yield observado da carteira geradora de renda, anualizado. Não é taxa de " +
  "retirada (decumulação) nem retorno total da carteira.";

function TrsEfetivaStat({ data }: { data: PassiveIncomeData }) {
  const defasagem = data.defasagem_meses ?? 0;
  const defasagemNote = defasagem >= DEFASAGEM_INFO_THRESHOLD && (
    <span className="block text-xs text-[var(--surface-muted-foreground)] mt-1">
      IRPF {data.ano_referencia_irpf} · {defasagem}m de defasagem
    </span>
  );
  return (
    <Stat
      label={
        <span className="inline-flex items-center gap-1">
          TRS efetiva
          <InfoTooltip ariaLabel="Sobre TRS efetiva" content={TRS_EFETIVA_TOOLTIP} />
        </span>
      }
      value={`${data.trs_efetiva_pct.toFixed(1)}%`}
      tone="neutral"
      sublabel={defasagemNote}
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
              <span className="text-[var(--semantic-alert-on-tint)]">
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
export { formatProbability };
