/**
 * Report Premium UI v2.8 (ADR-148) — render dos `ComparisonItem[]` produzidos
 * pelo `SnapshotChangelogBuilder`. Tabela "antes → depois" com delta_pct +
 * delta_signal por seção. Tokens-only (zero hex literal — ADR-076).
 *
 * Distinto de `ComparisonBlock` (1 par antes/depois free-form) — este aceita
 * a lista tipada do DTO Pydantic do backend.
 *
 * Título + caption são obrigatórios — sem moldura temporal a tabela não comunica
 * o que compara (decisão tomada após revisão product-designer 2026-05-11).
 */
import { MonetaryValue } from "../MonetaryValue";

export type DeltaSignal = "up" | "down" | "stable";
export type DirectionPositive = "up" | "down";

export interface ComparisonItemView {
  readonly section_id: string;
  readonly section_label: string;
  readonly before: number;
  readonly after: number;
  readonly delta_pct: number | null;
  readonly delta_signal: DeltaSignal;
  /** W2 (ADR-190 D3) — direção "boa pro usuário"; default "up" (pré-W2). */
  readonly direction_positive?: DirectionPositive;
}

// Glifo comunica a direção REAL do movimento; a cor comunica o julgamento
// (favorável/desfavorável) — independentes por decisão de UX da W2
// (dívida ↑ = seta ▲ vermelha, nunca seta invertida).
const SIGNAL_GLYPH: Record<DeltaSignal, string> = {
  up: "▲",
  down: "▼",
  stable: "•",
};

function deltaColor(item: ComparisonItemView): string {
  if (item.delta_signal === "stable") return "var(--surface-muted-foreground)";
  const positive = item.delta_signal === (item.direction_positive ?? "up");
  return positive ? "var(--semantic-success)" : "var(--semantic-danger)";
}

// WCAG 1.4.1: a cor passa a carregar julgamento independente da seta, então a
// célula Δ verbaliza o julgamento para leitores de tela.
function deltaAriaLabel(item: ComparisonItemView): string {
  if (item.delta_signal === "stable") {
    return `${item.section_label} sem variação relevante`;
  }
  // Heurística de plural pt-BR idêntica à de narratives.py (última palavra em "s").
  const plural = /s$/i.test(item.section_label.trim().split(" ").pop() ?? "");
  const movement =
    item.delta_signal === "up"
      ? plural ? "aumentaram" : "aumentou"
      : plural ? "diminuíram" : "diminuiu";
  const pct = item.delta_pct !== null && isFinite(item.delta_pct)
    ? `${Math.abs(item.delta_pct).toFixed(1).replace(".", ",")}%`
    : "";
  const positive = item.delta_signal === (item.direction_positive ?? "up");
  const judgment = positive ? "favorável" : "desfavorável";
  return `${[item.section_label, movement, pct].filter(Boolean).join(" ")}, ${judgment}`;
}

const DEFAULT_TITLE = "Variação vs. relatório anterior";
const DEFAULT_CAPTION =
  "Comparando o último relatório publicado com o atual. Apenas variações relevantes são listadas.";

function formatDeltaPct(pct: number | null): string {
  if (pct === null || !isFinite(pct)) return "—";
  const rounded = Math.abs(pct).toFixed(1).replace(".", ",");
  return `${rounded}%`;
}

export function ComparisonItemsBlock({
  items,
  className,
  title = DEFAULT_TITLE,
  caption = DEFAULT_CAPTION,
}: {
  readonly items: readonly ComparisonItemView[];
  readonly className?: string;
  readonly title?: string;
  readonly caption?: string;
}) {
  if (!items || items.length === 0) return null;
  return (
    <div
      className={className}
      data-testid="comparison-items-block"
      style={{
        background: "var(--surface-background)",
        borderRadius: "var(--radius-card, 12px)",
        padding: "var(--space-lg, 16px)",
        border: "1px solid var(--surface-border)",
        boxShadow: "var(--shadow-card)",
        margin: "var(--space-md, 12px) 0",
      }}
    >
      <header style={{ marginBottom: "var(--space-sm, 8px)" }}>
        <h4
          style={{
            margin: 0,
            fontFamily: "var(--font-display)",
            fontSize: "var(--report-font-size-md, 14px)",
            fontWeight: 700,
            color: "var(--brand-primary)",
            letterSpacing: "0.01em",
          }}
        >
          {title}
        </h4>
        {caption ? (
          <p
            style={{
              margin: "4px 0 0 0",
              fontSize: "var(--report-font-size-sm, 12px)",
              color: "var(--surface-muted-foreground)",
              lineHeight: 1.4,
            }}
          >
            {caption}
          </p>
        ) : null}
      </header>
      <table
        style={{
          width: "100%",
          borderCollapse: "collapse",
          fontFamily: "var(--font-body)",
          fontSize: "var(--report-font-size-md, 14px)",
        }}
      >
        <thead>
          <tr style={{ textAlign: "left", color: "var(--surface-muted-foreground)" }}>
            <th scope="col" style={{ padding: "6px 8px", fontWeight: 600 }}>Seção</th>
            <th scope="col" style={{ padding: "6px 8px", fontWeight: 600, textAlign: "right" }}>Antes</th>
            <th scope="col" style={{ padding: "6px 8px", fontWeight: 600, textAlign: "right" }}>Depois</th>
            <th scope="col" style={{ padding: "6px 8px", fontWeight: 600, textAlign: "right" }}>Δ</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={item.section_id}
              data-section-id={item.section_id}
              data-delta-signal={item.delta_signal}
              style={{ borderTop: "1px solid var(--surface-border)" }}
            >
              <td style={{ padding: "8px", color: "var(--brand-primary)", fontWeight: 600 }}>
                {item.section_label}
              </td>
              <td style={{ padding: "8px", textAlign: "right" }}>
                <MonetaryValue value={item.before} />
              </td>
              <td style={{ padding: "8px", textAlign: "right" }}>
                <MonetaryValue value={item.after} />
              </td>
              <td
                aria-label={deltaAriaLabel(item)}
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
                {formatDeltaPct(item.delta_pct)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
