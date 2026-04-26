"use client";

import type { CSSProperties } from "react";

/** v2.E.6 — Legenda agrupada custom para Receita vs Despesa Mês a Mês.
 *
 * Paridade visual com `EXEMPLO_DE_RELATORIO.html:7902-7938`. Renderiza
 * dois grupos ("Receitas" + "Despesas") com swatches clicaveis. Toggle
 * imperativo no chart fica do lado do consumidor — esta componente apenas
 * reflete o estado e propaga clicks. Componente puro, sem state interno.
 */
export interface RDMLegendItem {
  readonly index: number;
  readonly label: string;
  readonly color: string;
  readonly hidden: boolean;
}

export interface RDMLegendProps {
  readonly receitas: readonly RDMLegendItem[];
  readonly despesas: readonly RDMLegendItem[];
  readonly onToggle: (index: number) => void;
  readonly className?: string;
}

export function RDMLegend({ receitas, despesas, onToggle, className }: RDMLegendProps) {
  return (
    <div className={className} style={CONTAINER_STYLE} data-rdm-legend>
      <LegendGroup title="Receitas" items={receitas} onToggle={onToggle} />
      <LegendGroup title="Despesas" items={despesas} onToggle={onToggle} />
    </div>
  );
}

function LegendGroup({
  title,
  items,
  onToggle,
}: {
  readonly title: string;
  readonly items: readonly RDMLegendItem[];
  readonly onToggle: (index: number) => void;
}) {
  if (items.length === 0) return null;
  return (
    <div style={GROUP_STYLE} data-legend-group={title.toLowerCase()}>
      <div style={GROUP_TITLE_STYLE}>{title}</div>
      <div style={ITEMS_ROW_STYLE}>
        {items.map((item) => (
          <button
            key={`${title}-${item.index}`}
            type="button"
            onClick={() => onToggle(item.index)}
            data-legend-swatch
            data-legend-hidden={item.hidden ? "true" : "false"}
            aria-pressed={!item.hidden}
            style={item.hidden ? HIDDEN_ITEM_STYLE : ITEM_STYLE}
          >
            <span style={{ ...SWATCH_STYLE, background: item.color }} aria-hidden="true" />
            <span style={item.hidden ? STRIKE_LABEL_STYLE : LABEL_STYLE}>{item.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

const CONTAINER_STYLE: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 10,
  marginTop: 10,
};

const GROUP_STYLE: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 4,
};

const GROUP_TITLE_STYLE: CSSProperties = {
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: "0.5px",
  textTransform: "uppercase",
  color: "var(--surface-muted-foreground)",
};

const ITEMS_ROW_STYLE: CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: 10,
};

const ITEM_STYLE: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 6,
  padding: "4px 8px",
  border: "1px solid var(--surface-border)",
  borderRadius: 9999,
  background: "transparent",
  cursor: "pointer",
  fontSize: 12,
  fontFamily: "var(--font-body)",
  color: "var(--surface-foreground)",
  transition: "opacity 0.15s",
};

const HIDDEN_ITEM_STYLE: CSSProperties = {
  ...ITEM_STYLE,
  opacity: 0.5,
};

const SWATCH_STYLE: CSSProperties = {
  width: 10,
  height: 10,
  borderRadius: 2,
  display: "inline-block",
};

const LABEL_STYLE: CSSProperties = {
  textDecoration: "none",
};

const STRIKE_LABEL_STYLE: CSSProperties = {
  textDecoration: "line-through",
};
