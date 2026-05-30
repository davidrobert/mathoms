"use client";

import type { CardVariant } from "@/generated/report-layout";
import type {
  RealEstateAlerta,
  RealEstateBenchmarks,
  RealEstateData,
  RealEstateExcludedProperty,
  RealEstateImovel,
  RealEstateSpreads,
} from "@/types/report-analysis";
import { MonetaryValue } from "../MonetaryValue";
import { ReportCard } from "../ReportCard";

interface RealEstateYieldCardProps {
  data: RealEstateData | null | undefined;
}

const TABLE_PAGE = 5;
const HUGE_NEGATIVE_SPREAD_PP = -3.0;

/** Onda 2 P-C (ADR-216) — cap rate líquido + tríade benchmarks + tabela por imóvel. */
export function RealEstateYieldCard({ data }: RealEstateYieldCardProps) {
  if (!data) return <RealEstateEmptyState />;
  if (data.cap_rate_liquido_pct === null) {
    return <RealEstateEmptyState reason="sem_dado" excluded={data.excluded_properties} />;
  }
  return (
    <ReportCard
      size="full"
      title="Imóveis de investimento — Yield vs renda fixa e FIIs"
      variant={pickVariant(data)}
    >
      <RealEstateHero data={data} />
      <ValorMercadoNudge imoveis={data.imoveis} />
      <RealEstateImoveisTable imoveis={data.imoveis} />
      <RealEstateAlertasBlock alertas={data.alertas} />
      <RealEstateExcluded excluded={data.excluded_properties} />
      <RealEstateFooter benchmarks={data.benchmarks} />
    </ReportCard>
  );
}

/**
 * Nudge ADR-227 §D5: aparece quando algum imóvel locado/comercial ainda
 * usa ``valor_imovel_origem === "irpf"`` — sinaliza ao usuário que pode
 * declarar valor de mercado para refletir yield real. Copy honest:
 * yield é calculado sobre IRPF; mercado pode estar diferente.
 */
function ValorMercadoNudge({ imoveis }: { imoveis: readonly RealEstateImovel[] }) {
  const pendingCount = imoveis.filter((im) => im.valor_imovel_origem === "irpf").length;
  if (pendingCount === 0) return null;
  return (
    <aside
      className="rounded-md border p-3 text-sm"
      style={{
        borderColor: "var(--semantic-info-financial)",
        backgroundColor: "var(--surface-muted)",
        color: "var(--surface-foreground)",
      }}
      role="note"
    >
      <strong>Yield calculado sobre valor declarado no IRPF.</strong>{" "}
      {pendingCount === 1
        ? "1 imóvel ainda não tem valor de mercado declarado."
        : `${pendingCount} imóveis ainda não têm valor de mercado declarado.`}{" "}
      Se o valor mudou, atualize em{" "}
      <a
        href="/config?tab=members"
        className="underline"
        style={{ color: "var(--brand-info)" }}
      >
        Configurações &rsaquo; Membros
      </a>{" "}
      para refletir o retorno real.
    </aside>
  );
}

// ───────────────────────── Hero ────────────────────────────────────────────

function RealEstateHero({ data }: { data: RealEstateData }) {
  const cap = data.cap_rate_liquido_pct ?? 0;
  const oportunidadeCdi = data.spread_brl_anual.vs_cdi;
  return (
    <div className="grid gap-6 md:grid-cols-[1fr_1fr]">
      <div className="flex flex-col gap-2">
        <p className="text-sm uppercase tracking-wide text-[var(--surface-muted-foreground)]">
          Cap rate líquido
        </p>
        <p className="font-mono text-4xl font-semibold tabular-nums leading-none">
          {cap.toFixed(2).replace(".", ",")}%
          <span className="ml-2 text-xl text-[var(--surface-muted-foreground)]">a.a.</span>
        </p>
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          {(data.concentracao_pct ?? 0).toFixed(1).replace(".", ",")}% do patrimônio
          líquido em imóveis · {data.imoveis.length}{" "}
          {data.imoveis.length === 1 ? "imóvel" : "imóveis"} de investimento
        </p>
      </div>
      <div className="flex flex-col gap-2 border-t pt-4 md:border-t-0 md:border-l md:pl-6 md:pt-0 border-[var(--surface-border)]">
        <p className="text-sm uppercase tracking-wide text-[var(--surface-muted-foreground)]">
          Spread anual vs CDI
        </p>
        <MonetaryValue value={oportunidadeCdi} size="hero" signed />
        <RealEstateBarChart cap={cap} benchmarks={data.benchmarks} spreads={data.spreads_pp} />
      </div>
    </div>
  );
}

function RealEstateBarChart({
  cap,
  benchmarks,
  spreads,
}: {
  cap: number;
  benchmarks: RealEstateBenchmarks;
  spreads: RealEstateSpreads;
}) {
  const rows = [
    { label: "Cap líq.", value: cap, spread: 0, isSelf: true },
    { label: "CDI líq.", value: benchmarks.cdi_liquido_pct, spread: spreads.vs_cdi },
    { label: "NTN-B real", value: benchmarks.ntnb_liquido_pct, spread: spreads.vs_ntnb },
    { label: "IFIX 12m", value: benchmarks.ifix_yield_pct, spread: spreads.vs_ifix },
  ];
  const maxValue = Math.max(...rows.map((r) => Math.max(r.value, 0.01)));
  return (
    <ul className="mt-2 space-y-1" aria-label="Comparação cap rate vs benchmarks">
      {rows.map((r) => (
        <li key={r.label} className="flex items-center gap-2 text-xs">
          <span className="w-20 text-[var(--surface-muted-foreground)]">{r.label}</span>
          <span
            aria-hidden="true"
            className="block h-2 rounded-full"
            style={{
              width: `${Math.max((r.value / maxValue) * 100, 2)}%`,
              backgroundColor: r.isSelf
                ? "var(--brand-primary)"
                : "var(--surface-muted-foreground)",
              opacity: r.isSelf ? 1 : 0.5,
            }}
          />
          <span className="font-mono tabular-nums">{r.value.toFixed(2).replace(".", ",")}%</span>
        </li>
      ))}
    </ul>
  );
}

// ───────────────────────── Tabela por imóvel ───────────────────────────────

function RealEstateImoveisTable({ imoveis }: { imoveis: readonly RealEstateImovel[] }) {
  if (imoveis.length <= 1) return null;
  const top = imoveis.slice(0, TABLE_PAGE);
  return (
    <div className="mt-6">
      <p className="mb-2 text-sm font-semibold text-[var(--surface-foreground)]">
        Detalhe por imóvel
      </p>
      <table className="w-full text-sm">
        <caption className="sr-only">
          Imóveis de investimento ordenados por valor IRPF descendente — cap rate líquido por imóvel
        </caption>
        <thead className="text-[var(--surface-muted-foreground)]">
          <tr className="text-left">
            <th className="py-1 pr-2 font-normal">Imóvel</th>
            <th className="py-1 pr-2 text-right font-normal">Valor IRPF</th>
            <th className="py-1 pr-2 text-right font-normal">Aluguel/mês</th>
            <th className="py-1 pr-2 text-right font-normal">Cap líq.</th>
            <th className="py-1 font-normal">Status</th>
          </tr>
        </thead>
        <tbody>
          {top.map((im) => (
            <RealEstateRow key={im.property_id} im={im} />
          ))}
        </tbody>
      </table>
      {imoveis.length > TABLE_PAGE && (
        <p className="mt-2 text-xs text-[var(--surface-muted-foreground)]">
          + {imoveis.length - TABLE_PAGE}{" "}
          {imoveis.length - TABLE_PAGE === 1 ? "imóvel" : "imóveis"} adicional(is) não exibido(s).
        </p>
      )}
    </div>
  );
}

function RealEstateRow({ im }: { im: RealEstateImovel }) {
  return (
    <tr className="border-t border-[var(--surface-border)]">
      <td className="py-2 pr-2">
        <span className="block">{im.descricao}</span>
        {im.imobiliaria_nome && (
          <span className="block text-xs text-[var(--surface-muted-foreground)]">
            {im.imobiliaria_nome}
          </span>
        )}
      </td>
      <td className="py-2 pr-2 text-right font-mono tabular-nums">
        <MonetaryValue value={im.valor_imovel} />
      </td>
      <td className="py-2 pr-2 text-right font-mono tabular-nums">
        {im.aluguel_mensal_bruto !== null ? (
          <MonetaryValue value={im.aluguel_mensal_bruto} />
        ) : (
          <span className="text-[var(--surface-muted-foreground)]">—</span>
        )}
      </td>
      <td className="py-2 pr-2 text-right font-mono tabular-nums">
        {im.cap_rate_liquido_pct !== null
          ? `${im.cap_rate_liquido_pct.toFixed(2).replace(".", ",")}%`
          : "—"}
      </td>
      <td className="py-2">
        <StatusBadge status={im.status_contrato} />
      </td>
    </tr>
  );
}

function StatusBadge({
  status,
}: {
  status: RealEstateImovel["status_contrato"];
}) {
  const label =
    status === "atualizado"
      ? "Atualizado"
      : status === "reajuste_pendente"
        ? "Reajuste pendente"
        : status === "sem_renda"
          ? "Sem renda"
          : "—";
  const tone =
    status === "atualizado"
      ? "var(--semantic-gain)"
      : status === "reajuste_pendente"
        ? "var(--brand-warning)"
        : "var(--surface-muted-foreground)";
  return (
    <span className="inline-flex items-center gap-1 text-xs">
      <span
        aria-hidden="true"
        className="inline-block h-2 w-2 rounded-full"
        style={{ backgroundColor: tone }}
      />
      <span aria-label={`Status do contrato: ${label}`}>{label}</span>
    </span>
  );
}

// ───────────────────────── Alertas + excluded + footer ────────────────────

function RealEstateAlertasBlock({ alertas }: { alertas: readonly RealEstateAlerta[] }) {
  if (alertas.length === 0) return null;
  return (
    <ul className="mt-4 space-y-2" aria-label="Alertas do card de imóveis">
      {alertas.map((a, idx) => (
        <li
          key={`${a.code}-${idx}`}
          className="rounded border-l-4 px-3 py-2 text-sm"
          style={{
            borderLeftColor:
              a.severity === "critical"
                ? "var(--semantic-loss)"
                : a.severity === "warning"
                  ? "var(--brand-warning)"
                  : "var(--surface-muted-foreground)",
            backgroundColor: "color-mix(in_srgb, var(--surface-background) 50%, transparent)",
          }}
        >
          <p className="font-semibold text-[var(--surface-foreground)]">{labelForAlerta(a.code)}</p>
          <p className="text-[var(--surface-muted-foreground)]">{a.context}</p>
        </li>
      ))}
    </ul>
  );
}

function labelForAlerta(code: RealEstateAlerta["code"]): string {
  if (code === "concentracao_alta") return "Concentração elevada em imóveis";
  if (code === "spread_critico") return "Spread crítico vs renda fixa";
  if (code === "aluguel_sem_dado") return "Aluguel por imóvel estimado";
  return "Contrato com reajuste pendente";
}

function RealEstateExcluded({
  excluded,
}: {
  excluded: readonly { readonly descricao: string; readonly motivo: string }[];
}) {
  if (excluded.length === 0) return null;
  return (
    <details className="mt-4 text-xs text-[var(--surface-muted-foreground)]">
      <summary className="cursor-pointer">
        {excluded.length} {excluded.length === 1 ? "imóvel" : "imóveis"} não incluído(s) no cálculo
      </summary>
      <ul className="mt-2 space-y-1">
        {excluded.map((e, idx) => (
          <li key={`${e.descricao}-${idx}`}>
            <span className="font-semibold">{e.descricao}</span> — {e.motivo}
          </li>
        ))}
      </ul>
    </details>
  );
}

function RealEstateFooter({ benchmarks }: { benchmarks: RealEstateBenchmarks }) {
  return (
    <p className="mt-4 text-xs text-[var(--surface-muted-foreground)]">
      Cap rate líquido = (aluguel anual − IR carnê-leão − taxa adm − IPTU − condomínio − manutenção
      1% − vacância) ÷ valor IRPF. Benchmarks líquidos snapshot {benchmarks.as_of_date} — CDI ×
      0,825 (IR RF efetivo 17,5%); NTN-B real × 0,85 (IR longo prazo 15%); IFIX isento PF.
    </p>
  );
}

// ───────────────────────── Empty state ────────────────────────────────────

function RealEstateEmptyState({
  reason,
  excluded = [],
}: {
  reason?: "sem_dado";
  excluded?: readonly RealEstateExcludedProperty[];
} = {}) {
  return (
    <ReportCard
      size="full"
      title="Imóveis de investimento — Yield vs renda fixa e FIIs"
      variant="neutral"
    >
      <p className="text-base text-[var(--surface-foreground)]">
        {reason === "sem_dado"
          ? "Sem dados de aluguel suficientes para calcular cap rate líquido."
          : "Você não tem imóveis de investimento classificados no momento."}
      </p>
      <p className="mt-2 text-sm text-[var(--surface-muted-foreground)]">
        Carregue declarações IRPF recentes e classifique os imóveis em Configurações → Imóveis para
        ver cap rate, concentração e comparação com renda fixa e FIIs.
      </p>
      <RealEstateExcludedSummary excluded={excluded} />
    </ReportCard>
  );
}

/**
 * No empty state ``sem_dado``, lista os imóveis intencionalmente excluídos do
 * cálculo de yield (residência principal, desconhecido, etc.) — sem isso o
 * usuário não tem sinal de que o card não está quebrado, só não tem imóvel de
 * investimento elegível.
 */
function RealEstateExcludedSummary({
  excluded,
}: {
  excluded: readonly RealEstateExcludedProperty[];
}) {
  if (excluded.length === 0) return null;
  return (
    <div className="mt-4 border-t pt-4 border-[var(--surface-border)]">
      <p className="text-sm font-semibold text-[var(--surface-foreground)]">
        {excluded.length}{" "}
        {excluded.length === 1
          ? "imóvel foi excluído do cálculo de yield"
          : "imóveis foram excluídos do cálculo de yield"}
      </p>
      <ul className="mt-2 space-y-2 text-sm">
        {excluded.map((e, idx) => (
          <li key={`${e.property_id}-${idx}`}>
            <span className="font-semibold text-[var(--surface-foreground)]">{e.descricao}</span>{" "}
            <span className="text-[var(--surface-muted-foreground)]">({e.classification})</span>
            <span className="block text-[var(--surface-muted-foreground)]">{e.motivo}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ───────────────────────── Variant picker ─────────────────────────────────

function pickVariant(data: RealEstateData): CardVariant {
  const hasCritical = data.alertas.some((a) => a.severity === "critical");
  if (hasCritical) return "critical";
  const hasWarn = data.alertas.some((a) => a.severity === "warning");
  if (hasWarn) return "warn";
  const spreadCdi = data.spreads_pp.vs_cdi;
  if (spreadCdi <= HUGE_NEGATIVE_SPREAD_PP) return "warn";
  return "neutral";
}
