import type { CardVariant } from "@/generated/report-layout";
import type { RatiosData, RentabilidadeRatio } from "@/types/report-analysis";
import { ReportCard } from "../ReportCard";

interface RentabilidadeCardProps {
  ratios: RatiosData | undefined;
}

const DEFASAGEM_BADGE_LIMITE = 18;

/** Track T06 / ADR-191 — card Rentabilidade exibe TRS efetiva + cobertura essencial. */
export function RentabilidadeCard({ ratios }: RentabilidadeCardProps) {
  if (!ratios) return null;

  const nested = readRentabilidade(ratios);
  if (nested === null) {
    return <RentabilidadeFallbackCard ratios={ratios} />;
  }

  if (nested.status === "sem_irpf") return <RentabilidadeEmptyState kind="sem_irpf" />;
  if (nested.status === "gerador_zero")
    return <RentabilidadeEmptyState kind="gerador_zero" ratio={nested} />;

  return <RentabilidadeFullCard ratio={nested} />;
}

function readRentabilidade(ratios: RatiosData): RentabilidadeRatio | null {
  return ratios.rentabilidade ?? null;
}

/** Back-compat: workspaces antes do PR-A (sem campo aninhado) caem aqui. */
function RentabilidadeFallbackCard({ ratios }: { ratios: RatiosData }) {
  const valor = ratios.rentabilidade_pct;
  return (
    <ReportCard size="full" title="Renda passiva sobre patrimônio (TRS)" variant="feature">
      <p className="font-mono text-2xl tabular-nums">
        {typeof valor === "number" ? `${valor.toFixed(2)}%` : String(valor ?? "N/D")}
      </p>
      <p className="mt-2 text-sm text-[var(--surface-muted-foreground)]">
        Yield observado sobre patrimônio gerador. Contexto detalhado disponível
        após reprocessar o relatório.
      </p>
    </ReportCard>
  );
}

function RentabilidadeFullCard({ ratio }: { ratio: RentabilidadeRatio }) {
  const variant = pickVariant(ratio);
  const valorPct = ratio.valor_pct ?? 0;
  const cobertura = ratio.cobertura_despesa_essencial_pct;
  const isDefasado = isDataDefasada(ratio.defasagem_meses);
  return (
    <ReportCard size="full" title="Renda passiva sobre patrimônio (TRS)" variant={variant}>
      <div className="grid gap-6 md:grid-cols-[1fr_1fr]">
        <RentabilidadeHeroBlock valorPct={valorPct} metaPct={ratio.meta_pct} />
        <RentabilidadeContextBlock
          cobertura={cobertura}
          showSemDadosEssencial={ratio.status === "sem_dados_essencial"}
          anoBase={ratio.ano_base}
          defasagemMeses={ratio.defasagem_meses}
          isDefasado={isDefasado}
        />
      </div>
      <p className="mt-4 text-xs text-[var(--surface-muted-foreground)]">
        TRS efetiva — yield anualizado da renda passiva observada via IRPF sobre o patrimônio
        gerador (carteira de renda). Não confundir com retorno total da carteira.
      </p>
    </ReportCard>
  );
}

function RentabilidadeHeroBlock({ valorPct, metaPct }: { valorPct: number; metaPct: number }) {
  const diff = valorPct - metaPct;
  return (
    <div className="flex flex-col gap-1">
      <p className="text-sm uppercase tracking-wide text-[var(--surface-muted-foreground)]">
        TRS efetiva
      </p>
      <p className="font-mono text-4xl font-semibold tabular-nums leading-none">
        {valorPct.toFixed(2).replace(".", ",")}%
        <span className="ml-2 text-xl text-[var(--surface-muted-foreground)]">a.a.</span>
      </p>
      <p className="text-sm text-[var(--surface-muted-foreground)]">
        Meta de referência: {metaPct.toFixed(1).replace(".", ",")}% a.a.
        {" · "}
        {diff >= 0 ? "+" : ""}
        {diff.toFixed(2).replace(".", ",")} pp vs. meta
      </p>
    </div>
  );
}

function RentabilidadeContextBlock({
  cobertura,
  showSemDadosEssencial,
  anoBase,
  defasagemMeses,
  isDefasado,
}: {
  cobertura: number | null;
  showSemDadosEssencial: boolean;
  anoBase: number | null;
  defasagemMeses: number | null;
  isDefasado: boolean;
}) {
  return (
    <div className="flex flex-col gap-2 border-t pt-4 md:border-t-0 md:border-l md:pl-6 md:pt-0 border-[var(--surface-border)]">
      <p className="text-sm uppercase tracking-wide text-[var(--surface-muted-foreground)]">
        Cobertura essencial
      </p>
      {cobertura !== null ? (
        <p className="font-mono text-3xl font-semibold tabular-nums leading-none">
          {cobertura.toFixed(1).replace(".", ",")}%
        </p>
      ) : (
        <p className="text-base text-[var(--surface-muted-foreground)]">—</p>
      )}
      <p className="text-sm text-[var(--surface-muted-foreground)]">
        {cobertura !== null
          ? "da despesa essencial mensal coberta pela renda passiva atual."
          : showSemDadosEssencial
            ? "Categorização incompleta — cobertura essencial não disponível."
            : "—"}
      </p>
      <RentabilidadeFooter
        anoBase={anoBase}
        defasagemMeses={defasagemMeses}
        isDefasado={isDefasado}
      />
    </div>
  );
}

function RentabilidadeFooter({
  anoBase,
  defasagemMeses,
  isDefasado,
}: {
  anoBase: number | null;
  defasagemMeses: number | null;
  isDefasado: boolean;
}) {
  if (anoBase === null && defasagemMeses === null) return null;
  return (
    <p className="mt-2 flex items-center gap-2 text-xs text-[var(--surface-muted-foreground)]">
      {anoBase !== null && <span>Ano-base IRPF {anoBase}</span>}
      {defasagemMeses !== null && (
        <span aria-hidden="true" className="opacity-60">
          ·
        </span>
      )}
      {defasagemMeses !== null && (
        <span>
          {defasagemMeses} {defasagemMeses === 1 ? "mês" : "meses"} de defasagem
        </span>
      )}
      {isDefasado && (
        <span
          aria-label="Dado defasado — atualize seu IRPF"
          className="ml-1 inline-flex items-center rounded-full bg-[color-mix(in_srgb,var(--brand-warning)_18%,transparent)] px-2 py-0.5 text-[var(--brand-warning)]"
        >
          Dado defasado
        </span>
      )}
    </p>
  );
}

function RentabilidadeEmptyState({
  kind,
  ratio,
}: {
  kind: "sem_irpf" | "gerador_zero";
  ratio?: RentabilidadeRatio;
}) {
  const title = "Renda passiva sobre patrimônio (TRS)";
  if (kind === "sem_irpf") {
    return (
      <ReportCard size="full" title={title} variant="neutral">
        <p className="text-base text-[var(--surface-foreground)]">
          Indicador indisponível — precisamos do seu IRPF para calcular TRS efetiva.
        </p>
        <p className="mt-2 text-sm text-[var(--surface-muted-foreground)]">
          Carregue a declaração mais recente em Documentos → Adicionar.
        </p>
      </ReportCard>
    );
  }
  // gerador_zero
  return (
    <ReportCard size="full" title={title} variant="neutral">
      <p className="text-base text-[var(--surface-foreground)]">
        Sem patrimônio gerador identificado nesta carteira.
      </p>
      <p className="mt-2 text-sm text-[var(--surface-muted-foreground)]">
        TRS efetiva é calculada apenas quando há ativos geradores de renda passiva
        (ações, fundos imobiliários, renda fixa, imóveis de investimento).
      </p>
      {ratio?.ano_base !== undefined && ratio.ano_base !== null && (
        <p className="mt-3 text-xs text-[var(--surface-muted-foreground)]">
          Ano-base IRPF {ratio.ano_base}
        </p>
      )}
    </ReportCard>
  );
}

function pickVariant(ratio: RentabilidadeRatio): CardVariant {
  if (ratio.status !== "ok" || ratio.valor_pct === null) return "neutral";
  const diff = ratio.valor_pct - ratio.meta_pct;
  if (diff >= 0) return "success";
  if (diff >= -1) return "warn";
  return "critical";
}

export function isDataDefasada(defasagemMeses: number | null): boolean {
  return defasagemMeses !== null && defasagemMeses > DEFASAGEM_BADGE_LIMITE;
}
