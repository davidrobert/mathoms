"use client";

import { ChartGaugeSemi } from "@/components/report/charts/primitives";

export type ScoreClasse =
  | "Excelente"
  | "Bom"
  | "Regular"
  | "Ruim"
  | "Péssimo"
  | "Crítico";

const CLASSE_ACCENT: Record<ScoreClasse, string> = {
  Excelente: "#22B566",
  Bom: "#6EDBA0",
  Regular: "#F5BF2F",
  Ruim: "#F0924A",
  Péssimo: "#DC2640",
  Crítico: "#B91C1C",
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

/** ADR-117 · Fase 3 — card composto de Score Financeiro.
 *
 * Matching `.score-card-wrap` EXEMPLO_DE_RELATORIO.html linhas 979-1023.
 * Compõe: header badge + gauge semi + breakdown table + summary.
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
  const accent = CLASSE_ACCENT[classe];
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
            background: `${accent}20`,
            color: accent,
          }}
        >
          {classe}
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

      <ChartGaugeSemi
        value={value}
        max={max}
        centerValue={value.toFixed(1)}
        centerLabel={classe}
        fillColor={accent}
        height={220}
      />

      {breakdown && breakdown.length > 0 && (
        <div style={{ marginTop: 20, fontSize: 13 }}>
          <table style={{ width: "100%", borderCollapse: "separate", borderSpacing: 0 }}>
            <thead>
              <tr>
                {["Dimensão", "Valor", "Peso", "Contribuição"].map((h) => (
                  <th
                    key={h}
                    style={{
                      textAlign: "left",
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
                <tr key={`${row.dimensao}-${i}`}>
                  <td style={tdStyle}>{row.dimensao}</td>
                  <td style={{ ...tdStyle, textAlign: "center" }}>
                    {row.valor.toFixed(1)}
                    {row.max !== undefined ? ` / ${row.max}` : ""}
                  </td>
                  <td style={{ ...tdStyle, textAlign: "center" }}>
                    {row.peso !== undefined ? `${(row.peso * 100).toFixed(0)}%` : "—"}
                  </td>
                  <td style={{ ...tdStyle, textAlign: "center", fontWeight: 700 }}>
                    {row.contribuicao !== undefined ? row.contribuicao.toFixed(2) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
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
