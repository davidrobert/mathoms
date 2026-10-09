/** Estilos compartilhados pelos cards de gráfico do dashboard (`/plano` › Análise Financeira). */

export const TOOLTIP_ITEM_STYLE = {
  fontFamily: "var(--font-mono)",
  fontVariantNumeric: "tabular-nums",
} as const;

export const TOOLTIP_CONTENT_STYLE = {
  borderRadius: "var(--radius-md)",
  border: "1px solid var(--border)",
  background: "var(--popover)",
  color: "var(--popover-foreground)",
} as const;

// O recharts desenha o rótulo do tick fora do <g> do eixo: `className` no eixo não chega
// nele, e o default `fill="#666"` dá 2,55:1 sobre o card no dark. O tamanho vai em `style`
// porque é por ele que o <Text> mede a quebra de linha (sem ele, mede na fonte do body).
export const AXIS_TICK_STYLE = {
  fill: "var(--surface-muted-foreground)",
  fontSize: "var(--font-size-xs)",
} as const;
