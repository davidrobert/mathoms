/** Estilos compartilhados pelos cards de gráfico do dashboard (`/plano` › Mês corrente). */

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
