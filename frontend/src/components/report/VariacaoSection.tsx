/**
 * V0 — "O que mudou desde o último relatório" (SNAPSHOT_CHANGELOG_V3 W4/D6
 * · ADR-190 §Emenda 2026-07-09). Substitui os SectionSnapshotDiff por-seção
 * (W4-T07): manchete neutra do M_PL + tabela de indicadores por unidade.
 *
 * Estados degradados:
 * - `comparisons` null/vazio (primeiro relatório) ⇒ seção não renderiza.
 * - M_PL ausente ⇒ sem manchete, lista direto.
 * - lista vazia mas M_PL presente ⇒ só manchete + caption.
 *
 * Manchete é NEUTRA por decisão de design (sem cor semântica, sem glifo):
 * a variação total do PL mistura aporte + rendimento + mercado — julgar
 * "favorável/desfavorável" sem o waterfall (D5, deferida) induz erro.
 * A lista de indicadores mantém o julgamento W2 (ADR-190 D3):
 * cor = delta_signal vs direction_positive; glifo = direção real.
 */
import type { ComparisonItemRead, ReportAnalysisData } from "@/lib/api";
import { formatFullBRL } from "@/lib/format";
import { MonetaryValue } from "./MonetaryValue";

const HEADLINE_METRIC_ID = "M_PL";

const MONTH_LONG_PT = [
  "janeiro", "fevereiro", "março", "abril", "maio", "junho",
  "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
];

/** "202604" → "abril de 2026". Retorna null se o formato não casar. */
function formatPeriodLongPtBR(yyyymm: string): string | null {
  if (!/^\d{6}$/.test(yyyymm)) return null;
  const month = parseInt(yyyymm.slice(4, 6), 10);
  if (month < 1 || month > 12) return null;
  return `${MONTH_LONG_PT[month - 1]} de ${yyyymm.slice(0, 4)}`;
}

/** 3.04 → "3,0" (vírgula decimal pt-BR, 1 casa). */
function fmt1(value: number): string {
  return value.toFixed(1).replace(".", ",");
}

/** Antes/Depois por unidade não-monetária: pp → "12,0%"; meses → "6,0 meses". */
function formatUnitValue(value: number, unit: "pp" | "meses"): string {
  return unit === "pp" ? `${fmt1(value)}%` : `${fmt1(value)} meses`;
}

/** Δ por unidade não-monetária, com sinal explícito: "+3,0 pp" / "-0,2 mês". */
function formatUnitDelta(delta: number, unit: "pp" | "meses"): string {
  const sign = delta < 0 ? "-" : "+";
  const suffix = unit === "pp" ? "pp" : "mês";
  return `${sign}${fmt1(Math.abs(delta))} ${suffix}`;
}

// Glifo comunica a direção REAL do movimento; a cor comunica o julgamento
// (favorável/desfavorável) — independentes por decisão de UX da W2
// (dívida ↑ = seta ▲ vermelha, nunca seta invertida).
const SIGNAL_GLYPH: Record<ComparisonItemRead["delta_signal"], string> = {
  up: "▲",
  down: "▼",
  stable: "•",
};

function isPositiveForUser(item: ComparisonItemRead): boolean {
  return item.delta_signal === (item.direction_positive ?? "up");
}

function deltaColor(item: ComparisonItemRead): string {
  if (item.delta_signal === "stable") return "var(--surface-muted-foreground)";
  return isPositiveForUser(item)
    ? "var(--semantic-success)"
    : "var(--semantic-danger)";
}

/** Valor do movimento verbalizado/exibido na célula Δ, por unidade. */
function deltaDisplayValue(item: ComparisonItemRead): string {
  const unit = item.unit ?? "brl";
  if (unit === "pp" || unit === "meses") {
    return formatUnitDelta(item.after - item.before, unit);
  }
  if (item.delta_pct === null || !isFinite(item.delta_pct)) return "—";
  return `${fmt1(Math.abs(item.delta_pct))}%`;
}

// WCAG 1.4.1: a cor carrega julgamento independente da seta, então a célula Δ
// verbaliza o julgamento para leitores de tela (padrão herdado da W2).
function deltaAriaLabel(item: ComparisonItemRead): string {
  // Heurística de plural pt-BR idêntica à de narratives.py (última palavra em "s").
  const plural = /s$/i.test(item.section_label.trim().split(" ").pop() ?? "");
  const movement =
    item.delta_signal === "up"
      ? plural ? "subiram" : "subiu"
      : plural ? "caíram" : "caiu";
  const unit = item.unit ?? "brl";
  const value =
    unit === "pp" || unit === "meses"
      ? formatUnitDelta(item.after - item.before, unit).replace(/^[+-]/, "")
      : item.delta_pct !== null && isFinite(item.delta_pct)
        ? `${fmt1(Math.abs(item.delta_pct))}%`
        : "";
  const judgment = isPositiveForUser(item) ? "avaliação boa" : "avaliação ruim";
  return `${[item.section_label, movement, value].filter(Boolean).join(" ")} — ${judgment}`;
}

function buildSubtitle(previousLabel: string | null, currentLabel: string | null): string {
  if (previousLabel && currentLabel) {
    return `Este relatório (${currentLabel}) comparado ao anterior (${previousLabel}). Listamos apenas variações relevantes.`;
  }
  return "Comparado ao relatório anterior. Listamos apenas variações relevantes.";
}

function buildHeadlineAria(delta: number, previousLabel: string | null): string {
  const since = previousLabel ? `desde ${previousLabel}` : "desde o relatório anterior";
  if (delta === 0) return `Patrimônio líquido não variou ${since}`;
  const direction = delta > 0 ? "a mais" : "a menos";
  return `Patrimônio líquido variou ${formatFullBRL(Math.abs(delta))} ${direction} ${since}`;
}

const HEADLINE_CAPTION =
  "Mostramos a variação total do patrimônio no período. A separação entre " +
  "aporte, rendimento e efeito de mercado ainda não está disponível.";

function HeadlineDelta({
  item,
  previousLabel,
}: {
  readonly item: ComparisonItemRead;
  readonly previousLabel: string | null;
}) {
  const delta = item.after - item.before;
  return (
    <div style={{ margin: "var(--space-lg, 16px) 0 0 0" }}>
      {/* aria-label é proibido em <p> (aria-prohibited-attr); a frase
        * acessível vai em texto sr-only e o visual fica aria-hidden. */}
      <p style={{ margin: 0 }} data-testid="v0-headline">
        <span className="sr-only">{buildHeadlineAria(delta, previousLabel)}</span>
        {/* Neutra de propósito: cor de texto padrão, sem glifo, sem signed. */}
        <span
          aria-hidden="true"
          className="text-style-kpi-value tabular-nums"
          style={{ color: "var(--surface-foreground)" }}
        >
          {delta > 0 ? "+" : ""}
          <MonetaryValue value={delta} data-testid="v0-headline-delta" />
        </span>
      </p>
      <p
        data-testid="v0-headline-caption"
        style={{
          margin: "var(--space-sm, 8px) 0 0 0",
          fontSize: "var(--report-font-size-sm, 12px)",
          color: "var(--surface-muted-foreground)",
          lineHeight: 1.4,
        }}
      >
        {HEADLINE_CAPTION}
      </p>
    </div>
  );
}

function IndicatorsTable({ items }: { readonly items: readonly ComparisonItemRead[] }) {
  return (
    <table
      data-testid="v0-indicators-table"
      style={{
        width: "100%",
        borderCollapse: "collapse",
        marginTop: "var(--space-lg, 16px)",
        fontFamily: "var(--font-body)",
        fontSize: "var(--report-font-size-md, 14px)",
      }}
    >
      <thead>
        <tr style={{ textAlign: "left", color: "var(--surface-muted-foreground)" }}>
          <th scope="col" style={{ padding: "6px 8px", fontWeight: 600 }}>Indicador</th>
          <th scope="col" style={{ padding: "6px 8px", fontWeight: 600, textAlign: "right" }}>Antes</th>
          <th scope="col" style={{ padding: "6px 8px", fontWeight: 600, textAlign: "right" }}>Depois</th>
          <th scope="col" style={{ padding: "6px 8px", fontWeight: 600, textAlign: "right" }}>Δ</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => {
          const unit = item.unit ?? "brl";
          return (
            <tr
              key={item.section_id}
              data-section-id={item.section_id}
              data-delta-signal={item.delta_signal}
              style={{ borderTop: "1px solid var(--surface-border)" }}
            >
              <td style={{ padding: "8px", fontWeight: 600 }}>{item.section_label}</td>
              <td className="tabular-nums" style={{ padding: "8px", textAlign: "right" }}>
                {unit === "brl" ? (
                  <MonetaryValue value={item.before} />
                ) : (
                  formatUnitValue(item.before, unit)
                )}
              </td>
              <td className="tabular-nums" style={{ padding: "8px", textAlign: "right" }}>
                {unit === "brl" ? (
                  <MonetaryValue value={item.after} />
                ) : (
                  formatUnitValue(item.after, unit)
                )}
              </td>
              <td
                aria-label={deltaAriaLabel(item)}
                className="tabular-nums"
                style={{
                  padding: "8px",
                  textAlign: "right",
                  color: deltaColor(item),
                  fontWeight: 600,
                }}
              >
                <span aria-hidden="true" style={{ marginRight: 4 }}>
                  {SIGNAL_GLYPH[item.delta_signal]}
                </span>
                {deltaDisplayValue(item)}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export function VariacaoSection({ data }: { readonly data: ReportAnalysisData }) {
  const comparisons = data.comparisons ?? null;
  if (!comparisons || comparisons.length === 0) return null;

  const headline = comparisons.find((c) => c.section_id === HEADLINE_METRIC_ID) ?? null;
  const others = comparisons.filter((c) => c.section_id !== HEADLINE_METRIC_ID);
  const changed = others.filter((c) => c.delta_signal !== "stable");
  const stableCount = others.length - changed.length;

  const periods = data.comparison_periods ?? null;
  const currentLabel = periods ? formatPeriodLongPtBR(periods.current) : null;
  const previousLabel = periods ? formatPeriodLongPtBR(periods.previous) : null;

  return (
    <section
      id="V0"
      aria-labelledby="v0-title"
      data-report-section
      className="scroll-mt-20 mb-12"
    >
      <div
        data-testid="variacao-section-card"
        style={{
          background: "var(--surface-card)",
          border: "1px solid var(--surface-border)",
          borderRadius: "var(--radius-card)",
          boxShadow: "var(--shadow-card)",
          padding: "var(--space-2xl, 24px)",
          breakInside: "avoid",
          pageBreakInside: "avoid",
        }}
      >
        <h2
          id="v0-title"
          className="font-display text-2xl font-bold"
          style={{ margin: 0, color: "var(--surface-foreground)" }}
        >
          O que mudou desde o último relatório
        </h2>
        <p
          data-testid="v0-subtitle"
          style={{
            margin: "var(--space-xs, 4px) 0 0 0",
            fontSize: "var(--report-font-size-sm, 12px)",
            color: "var(--surface-muted-foreground)",
            lineHeight: 1.4,
          }}
        >
          {buildSubtitle(previousLabel, currentLabel)}
        </p>

        {headline && <HeadlineDelta item={headline} previousLabel={previousLabel} />}

        {changed.length > 0 && <IndicatorsTable items={changed} />}

        {stableCount > 0 && (
          <p
            data-testid="v0-stable-footer"
            style={{
              margin: "var(--space-lg, 16px) 0 0 0",
              fontSize: "var(--report-font-size-sm, 12px)",
              color: "var(--surface-muted-foreground)",
            }}
          >
            {stableCount === 1
              ? "Outro indicador acompanhado permaneceu estável."
              : `Outros ${stableCount} indicadores acompanhados permaneceram estáveis.`}
          </p>
        )}
      </div>
    </section>
  );
}
