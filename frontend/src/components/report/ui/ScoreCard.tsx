"use client";

import { ChartGaugeScore, type ScoreClasseKey } from "@/components/report/charts/primitives";

export type ScoreClasse =
  | "Excelente"
  | "Bom"
  | "Regular"
  | "Ruim"
  | "Péssimo"
  | "Crítico";

const CLASSE_TO_KEY: Record<ScoreClasse, ScoreClasseKey> = {
  Excelente: "excelente",
  Bom: "bom",
  Regular: "regular",
  Ruim: "ruim",
  Péssimo: "pessimo",
  Crítico: "critico",
};

export interface ScoreBreakdownRow {
  readonly dimensao: string;
  readonly valor: number;
  readonly max?: number;
  readonly peso?: number;
  readonly contribuicao?: number;
}

export interface ScoreCardProps {
  readonly value: number;
  readonly max?: number;
  readonly classe: ScoreClasse;
  readonly breakdown?: readonly ScoreBreakdownRow[];
  readonly formula?: string;
  /** v2.E.7 — parágrafo `chart-context` renderizado abaixo do título. */
  readonly context?: string;
  /** v2.E.7 — parágrafo `chart-conclusion` renderizado abaixo do breakdown. */
  readonly conclusion?: string;
  readonly className?: string;
}

/** Mapeia uma nota 0-10 para a chave de cor da escala. */
function noteToKey(nota: number, max: number): ScoreClasseKey {
  const scaled = (nota / max) * 10;
  if (scaled >= 8) return "excelente";
  if (scaled >= 6) return "bom";
  if (scaled >= 4) return "regular";
  if (scaled >= 2) return "ruim";
  return "pessimo";
}

/** ADR-117 · Card composto de Score Financeiro.
 *
 * Paridade visual com `EXEMPLO_DE_RELATORIO.html` (linhas 1808-1812 +
 * 7984-8194): header com badge da classe, gauge canvas custom, tabela
 * de breakdown com barras horizontais coloridas, summary footer.
 */
export function ScoreCard({
  value,
  max = 10,
  classe,
  breakdown,
  formula,
  context,
  conclusion,
  className,
}: ScoreCardProps) {
  const classeKey = CLASSE_TO_KEY[classe];
  const accent = `var(--score-classe-${classeKey})`;
  return (
    <section
      className={className}
      data-score-classe={classe}
      style={{
        background: "var(--surface-card)",
        borderRadius: "var(--radius-card, 12px)",
        padding: "var(--space-2xl, 24px)",
        boxShadow: "var(--shadow-card)",
        border: "1px solid var(--surface-border)",
        borderTop: `4px solid ${accent}`,
      }}
    >
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 8,
        }}
      >
        <h3
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "var(--report-font-size-lg, 16px)",
            fontWeight: 700,
            color: "var(--brand-primary)",
            margin: 0,
          }}
        >
          Score Financeiro
        </h3>
        <span
          data-level={classe}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            padding: "4px 14px",
            borderRadius: 20,
            fontSize: 12,
            fontWeight: 700,
            letterSpacing: "0.3px",
            textTransform: "uppercase",
            background: `color-mix(in srgb, ${accent} 14%, transparent)`,
            color: accent,
          }}
        >
          {value.toFixed(1).replace(".", ",")} — {classe}
        </span>
      </header>

      {context && (
        <p
          className="chart-context"
          style={{
            fontSize: "var(--report-font-size-base, 13px)",
            color: "var(--surface-muted-foreground)",
            margin: "8px 0 12px",
            lineHeight: 1.5,
          }}
        >
          {context}
        </p>
      )}

      <ChartGaugeScore
        value={value}
        max={max}
        classeLabel={classe.toUpperCase()}
        classeKey={classeKey}
      />

      {breakdown && breakdown.length > 0 && (
        <BreakdownTable breakdown={breakdown} max={max} />
      )}

      {conclusion && (
        <p
          className="chart-conclusion"
          style={{
            fontSize: "var(--report-font-size-base, 13px)",
            color: "var(--surface-foreground)",
            lineHeight: 1.5,
            margin: "12px 0 0",
            padding: "10px 14px",
            background: "var(--report-surface-conclusion-bg, var(--surface-muted))",
            borderRadius: "var(--radius-md, 6px)",
            borderLeft: "3px solid var(--brand-info)",
          }}
        >
          {conclusion}
        </p>
      )}

      {formula && (
        <p
          style={{
            textAlign: "center",
            color: "var(--surface-muted-foreground)",
            fontSize: 11,
            marginTop: 10,
            fontStyle: "italic",
            opacity: 0.7,
          }}
        >
          {formula}
        </p>
      )}
    </section>
  );
}

const tdStyle: React.CSSProperties = {
  padding: 10,
  borderBottom: "1px solid var(--surface-border)",
  verticalAlign: "middle",
};

function dotStyle(color: string): React.CSSProperties {
  return {
    width: 8,
    height: 8,
    borderRadius: "50%",
    background: color,
    flexShrink: 0,
  };
}

interface BreakdownTableProps {
  readonly breakdown: readonly ScoreBreakdownRow[];
  readonly max: number;
}

function BreakdownTable({ breakdown, max }: BreakdownTableProps) {
  return (
    <div style={{ marginTop: 20, fontSize: 13 }}>
      <table style={{ width: "100%", borderCollapse: "separate", borderSpacing: 0 }}>
        <thead>
          <tr>
            {["Dimensão", "Nota", "Peso", "Contrib."].map((h, i) => (
              <th
                key={h}
                style={{
                  textAlign: i === 0 ? "left" : "center",
                  fontWeight: 600,
                  color: "var(--surface-muted-foreground)",
                  fontSize: 10,
                  textTransform: "uppercase",
                  letterSpacing: "0.8px",
                  padding: "8px 10px",
                  borderBottom: "2px solid var(--surface-border)",
                }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {breakdown.map((row, i) => (
            <BreakdownRow key={`${row.dimensao}-${i}`} row={row} max={max} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface BreakdownRowProps {
  readonly row: ScoreBreakdownRow;
  readonly max: number;
}

function BreakdownRow({ row, max }: BreakdownRowProps) {
  const rowMax = row.max ?? max;
  const pct = Math.max(0, Math.min(100, (row.valor / rowMax) * 100));
  const noteColor = `var(--score-classe-${noteToKey(row.valor, rowMax)})`;
  return (
    <tr>
      <td style={tdStyle}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={dotStyle(noteColor)} aria-hidden="true" />
          <span style={{ fontWeight: 600 }}>{row.dimensao}</span>
        </div>
      </td>
      <td style={{ ...tdStyle, minWidth: 140 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div
            style={{
              flex: 1,
              height: 8,
              background: "var(--surface-muted)",
              borderRadius: 4,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${pct}%`,
                height: "100%",
                background: noteColor,
                borderRadius: 4,
                transition: "width 600ms cubic-bezier(0.16, 1, 0.3, 1)",
              }}
            />
          </div>
          <span
            style={{
              fontVariantNumeric: "tabular-nums",
              fontWeight: 700,
              minWidth: 32,
              textAlign: "right",
            }}
          >
            {row.valor.toFixed(1).replace(".", ",")}
          </span>
        </div>
      </td>
      <td style={{ ...tdStyle, textAlign: "center" }}>
        {row.peso !== undefined ? `${(row.peso * 100).toFixed(0)}%` : "—"}
      </td>
      <td
        style={{
          ...tdStyle,
          textAlign: "center",
          fontWeight: 700,
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {row.contribuicao !== undefined
          ? row.contribuicao.toFixed(2).replace(".", ",")
          : "—"}
      </td>
    </tr>
  );
}
