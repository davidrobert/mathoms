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

// Sob base alterada NENHUMA célula afirma mérito: as duas pontas do par foram consolidadas
// por métodos diferentes, e o que a cor chamaria de melhora pode ser só a mudança de método.
// O glifo de direção permanece — em `unit: "brl"` o sinal do movimento vive só nele e na cor.
function deltaColor(item: ComparisonItemRead, baseChanged: boolean): string {
  if (baseChanged || item.delta_signal === "stable") {
    return "var(--surface-muted-foreground)";
  }
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

/** Magnitude do movimento sem sinal — a direção já vem no verbo ("subiu"/"caiu"). */
function deltaSpokenValue(item: ComparisonItemRead): string {
  const unit = item.unit ?? "brl";
  if (unit === "pp" || unit === "meses") {
    return formatUnitDelta(item.after - item.before, unit).replace(/^[+-]/, "");
  }
  if (item.delta_pct === null || !isFinite(item.delta_pct)) return "";
  return `${fmt1(Math.abs(item.delta_pct))}%`;
}

/** Verbo do movimento; plural pt-BR pela heurística de narratives.py (última palavra em "s"). */
function deltaMovementVerb(item: ComparisonItemRead): string {
  const plural = /s$/i.test(item.section_label.trim().split(" ").pop() ?? "");
  if (item.delta_signal === "up") return plural ? "subiram" : "subiu";
  return plural ? "caíram" : "caiu";
}

// Paridade cor ≡ texto: a cor neutra e o nome acessível têm de cair juntos, senão o leitor
// de tela ouve um julgamento que a tela não faz (ou o inverso).
function deltaJudgment(item: ComparisonItemRead, baseChanged: boolean): string {
  if (baseChanged) return BASE_CHANGED_JUDGMENT;
  return isPositiveForUser(item) ? "avaliação boa" : "avaliação ruim";
}

// WCAG 1.4.1: a cor carrega julgamento independente da seta, então a célula Δ
// verbaliza o julgamento para leitores de tela (padrão herdado da W2).
function deltaAriaLabel(item: ComparisonItemRead, baseChanged: boolean): string {
  const falado = [item.section_label, deltaMovementVerb(item), deltaSpokenValue(item)];
  return `${falado.filter(Boolean).join(" ")} — ${deltaJudgment(item, baseChanged)}`;
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

const BASE_CHANGED_NOTE_ID = "v0-base-changed-note";

const BASE_CHANGED_JUDGMENT = "base de comparação alterada";

const BASE_CHANGED_NOTE =
  "A forma de consolidar lançamentos mudou entre os dois relatórios. As variações " +
  "abaixo comparam bases diferentes e não indicam, por si, melhora ou piora.";

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

/** Antes/Depois exibido, por unidade — mesma regra nas duas variantes. */
function valorExibido(item: ComparisonItemRead, ponta: "before" | "after") {
  const unit = item.unit ?? "brl";
  if (unit === "brl") return <MonetaryValue value={item[ponta]} />;
  return formatUnitValue(item[ponta], unit);
}

/** Δ com glifo + valor. Cor e rótulo acessível ficam no elemento que o
 *  hospeda: os três andam juntos nas duas variantes, senão a que perder um
 *  deles vira perda de acessibilidade disfarçada de responsividade. */
function DeltaCell({ item }: { readonly item: ComparisonItemRead }) {
  return (
    <>
      <span aria-hidden="true" style={{ marginRight: 4 }}>
        {SIGNAL_GLYPH[item.delta_signal]}
      </span>
      {deltaDisplayValue(item)}
    </>
  );
}

/** Abaixo de 640px a tabela de 4 colunas não cabe (min-content ~534px contra
 *  262px úteis a 390px) e a página não rola: a coluna Δ ficava inalcançável.
 *  O divisor é `sm:` e não `md:` porque a caixa de página A4 tem 703px — com
 *  `md:` (768px) o PAPEL receberia esta pilha em vez da tabela. */
function IndicatorsList({
  items,
  baseChanged,
}: {
  readonly items: readonly ComparisonItemRead[];
  readonly baseChanged: boolean;
}) {
  return (
    <ul
      className="sm:hidden"
      data-testid="v0-indicators-list"
      style={{
        listStyle: "none",
        margin: "var(--space-lg, 16px) 0 0 0",
        padding: 0,
        fontSize: "var(--report-font-size-md, 14px)",
      }}
    >
      {items.map((item) => (
        <IndicatorListItem key={item.section_id} item={item} baseChanged={baseChanged} />
      ))}
    </ul>
  );
}

function IndicatorListItem({
  item,
  baseChanged,
}: {
  readonly item: ComparisonItemRead;
  readonly baseChanged: boolean;
}) {
  return (
    <li
      data-base-changed={baseChanged ? "true" : undefined}
      data-delta-signal={item.delta_signal}
      data-section-id={item.section_id}
      style={{
        borderTop: "1px solid var(--surface-border)",
        padding: "10px 0",
        overflowWrap: "anywhere",
      }}
    >
      <div style={{ display: "flex", gap: 8, justifyContent: "space-between" }}>
        <span style={{ fontWeight: 600 }}>{item.section_label}</span>
        <span
          aria-describedby={baseChanged ? BASE_CHANGED_NOTE_ID : undefined}
          aria-label={deltaAriaLabel(item, baseChanged)}
          className="tabular-nums"
          style={{
            color: deltaColor(item, baseChanged),
            fontWeight: 600,
            whiteSpace: "nowrap",
          }}
        >
          <DeltaCell item={item} />
        </span>
      </div>
      <div
        className="tabular-nums"
        style={{
          color: "var(--surface-muted-foreground)",
          fontSize: "var(--report-font-size-sm, 12px)",
          marginTop: 2,
        }}
      >
        Antes {valorExibido(item, "before")} · Depois {valorExibido(item, "after")}
      </div>
    </li>
  );
}

function IndicatorsTable({
  items,
  baseChanged,
}: {
  readonly items: readonly ComparisonItemRead[];
  readonly baseChanged: boolean;
}) {
  return (
    <table
      className="hidden sm:table"
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
        {items.map((item) => (
          <IndicatorRow key={item.section_id} item={item} baseChanged={baseChanged} />
        ))}
      </tbody>
    </table>
  );
}

function IndicatorRow({
  item,
  baseChanged,
}: {
  readonly item: ComparisonItemRead;
  readonly baseChanged: boolean;
}) {
  return (
    <tr
      data-section-id={item.section_id}
      data-delta-signal={item.delta_signal}
      style={{ borderTop: "1px solid var(--surface-border)" }}
    >
      {/* O rótulo quebra; os valores não. É o que faz a tabela caber na caixa
        * A4 (703px) sem `table-layout: fixed`, que dividiria as colunas
        * igualmente e partiria os valores monetários. */}
      <td style={{ padding: "8px", fontWeight: 600, overflowWrap: "anywhere" }}>
        {item.section_label}
      </td>
      <td
        className="tabular-nums"
        style={{ padding: "8px", textAlign: "right", whiteSpace: "nowrap" }}
      >
        {valorExibido(item, "before")}
      </td>
      <td
        className="tabular-nums"
        style={{ padding: "8px", textAlign: "right", whiteSpace: "nowrap" }}
      >
        {valorExibido(item, "after")}
      </td>
      <td
        aria-describedby={baseChanged ? BASE_CHANGED_NOTE_ID : undefined}
        aria-label={deltaAriaLabel(item, baseChanged)}
        className="tabular-nums"
        data-base-changed={baseChanged ? "true" : undefined}
        style={{
          padding: "8px",
          textAlign: "right",
          color: deltaColor(item, baseChanged),
          fontWeight: 600,
        }}
      >
        <DeltaCell item={item} />
      </td>
    </tr>
  );
}

export function VariacaoSection({ data }: { readonly data: ReportAnalysisData }) {
  const comparisons = data.comparisons ?? null;
  if (!comparisons || comparisons.length === 0) return null;

  const headline = comparisons.find((c) => c.section_id === HEADLINE_METRIC_ID) ?? null;
  const others = comparisons.filter((c) => c.section_id !== HEADLINE_METRIC_ID);
  const changed = others.filter((c) => c.delta_signal !== "stable");
  const stableCount = others.length - changed.length;

  const baseChanged = data.comparison_base_changed === true;
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

        {/* Estado NOMEADO, nunca silêncio: sem esta nota a neutralização leria como
          * "nada relevante mudou", que é a leitura oposta à verdadeira. */}
        {baseChanged && (
          <p
            data-testid="v0-base-changed-note"
            id={BASE_CHANGED_NOTE_ID}
            style={{
              margin: "var(--space-md, 12px) 0 0 0",
              fontSize: "var(--report-font-size-sm, 12px)",
              color: "var(--surface-muted-foreground)",
              lineHeight: 1.4,
            }}
          >
            {BASE_CHANGED_NOTE}
          </p>
        )}

        {headline && <HeadlineDelta item={headline} previousLabel={previousLabel} />}

        {changed.length > 0 && (
          <>
            <IndicatorsTable items={changed} baseChanged={baseChanged} />
            <IndicatorsList items={changed} baseChanged={baseChanged} />
          </>
        )}

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
