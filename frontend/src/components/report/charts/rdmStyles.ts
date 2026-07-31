/** Estilos do chart "Receita vs Despesa — Mês a Mês" (v2.E.6).
 *
 * Movimento **mecânico** (mesmos valores, zero efeito visual) extraído de
 * `ReceitaDespesaMensalChart.tsx` em A40.l3, quando o texto novo daquele card
 * levou o arquivo a 510 linhas — acima do limite de 500 do gate T2
 * (`dev/audit_code_style.py`). Aquele texto voltou para a A40.l15, então hoje o
 * componente cabe **sem** esta extração: medido, 492 linhas se inlinado (7 de
 * folga em `main`, que já estava em 493). Fica porque devolve folga ao card que
 * a A40.l15 vai tocar, e reverter só re-inflaria o arquivo.
 *
 * Sem hex literal: tudo em `var(--*)`.
 */
export const CONTEXT_STYLE = {
  fontSize: 13,
  lineHeight: 1.5,
  color: "var(--surface-muted-foreground)",
  marginBottom: 12,
} as const;

export const CONCLUSION_STYLE = {
  fontSize: 12,
  lineHeight: 1.5,
  marginTop: 12,
  padding: "10px 12px",
  borderLeft: "3px solid var(--brand-info)",
  background: "color-mix(in srgb, var(--brand-info) 6%, var(--surface-card))",
  borderRadius: "var(--radius-md)",
  color: "var(--surface-foreground)",
} as const;

export const NAV_WRAPPER_STYLE = {
  marginBottom: 8,
} as const;

export const NAV_ROW_STYLE = {
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  gap: 12,
  userSelect: "none",
} as const;

export const NAV_BTN_STYLE = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  width: 28,
  height: 28,
  borderRadius: "50%",
  border: "1.5px solid var(--surface-border)",
  background: "var(--surface-background)",
  color: "var(--surface-foreground)",
  cursor: "pointer",
  fontSize: 16,
  fontWeight: 700,
} as const;

export const NAV_LABEL_STYLE = {
  fontSize: 12,
  fontWeight: 600,
  color: "var(--surface-foreground)",
  minWidth: 160,
  textAlign: "center" as const,
};

export const DOTS_STYLE = {
  display: "flex",
  gap: 5,
  justifyContent: "center",
  marginTop: 6,
} as const;

export const DOT_STYLE = {
  width: 6,
  height: 6,
  borderRadius: "50%",
  background: "var(--surface-border)",
} as const;

export const DOT_ACTIVE_STYLE = {
  ...DOT_STYLE,
  background: "var(--brand-accent)",
} as const;

export const PRINT_BLOCK_STYLE = {
  display: "flex",
  flexDirection: "column" as const,
  gap: 4,
  marginTop: 10,
  padding: "8px 12px",
  borderRadius: "var(--radius-md)",
  background: "var(--surface-muted)",
  fontSize: 12,
};
