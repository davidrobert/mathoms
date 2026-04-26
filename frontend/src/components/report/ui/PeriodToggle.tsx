"use client";

import type { CSSProperties } from "react";

export type Period = "3m" | "6m" | "12m" | "ytd";

export interface PeriodToggleProps {
  readonly value: Period;
  readonly onChange: (p: Period) => void;
  readonly periodLabel?: string;
  readonly className?: string;
}

interface PeriodOption {
  readonly id: Period;
  readonly label: string;
}

const OPTIONS: readonly PeriodOption[] = [
  { id: "3m", label: "3M" },
  { id: "6m", label: "6M" },
  { id: "12m", label: "12M" },
  { id: "ytd", label: "Ano" },
];

/** v2.E.1 — Segmented control para janela temporal de charts.
 *
 * Paridade visual com `EXEMPLO_DE_RELATORIO.html:381-413`, portado para
 * tokens do design system. Componente controlado: pai detém `value` e
 * reage via `onChange`.
 */
export function PeriodToggle({
  value,
  onChange,
  periodLabel,
  className,
}: PeriodToggleProps) {
  return (
    <div className={className} style={ROW_STYLE} data-period-toggle-row>
      <div role="tablist" aria-label="Janela temporal" style={GROUP_STYLE}>
        {OPTIONS.map((opt) => (
          <PeriodButton
            key={opt.id}
            option={opt}
            active={opt.id === value}
            onSelect={onChange}
          />
        ))}
      </div>
      {periodLabel ? (
        <span data-period-label style={LABEL_STYLE}>
          {periodLabel}
        </span>
      ) : null}
    </div>
  );
}

function PeriodButton({
  option,
  active,
  onSelect,
}: {
  readonly option: PeriodOption;
  readonly active: boolean;
  readonly onSelect: (p: Period) => void;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      data-period={option.id}
      data-active={active ? "true" : "false"}
      onClick={() => {
        if (!active) onSelect(option.id);
      }}
      style={active ? BTN_ACTIVE_STYLE : BTN_INACTIVE_STYLE}
    >
      {option.label}
    </button>
  );
}

const ROW_STYLE: CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  marginBottom: 4,
  flexWrap: "wrap",
  gap: 8,
};

const GROUP_STYLE: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 2,
  background: "var(--surface-card)",
  border: "1px solid var(--surface-border)",
  borderRadius: 9999,
  padding: 3,
  userSelect: "none",
};

const LABEL_STYLE: CSSProperties = {
  fontSize: 11,
  fontWeight: 500,
  color: "var(--surface-muted-foreground)",
  letterSpacing: "0.3px",
};

const BTN_BASE_STYLE: CSSProperties = {
  fontFamily: "var(--font-body)",
  fontSize: 11,
  fontWeight: 600,
  padding: "5px 14px",
  borderRadius: 9997,
  border: "none",
  transition: "all 0.2s ease",
  whiteSpace: "nowrap",
  letterSpacing: "0.3px",
  lineHeight: 1,
};

const BTN_ACTIVE_STYLE: CSSProperties = {
  ...BTN_BASE_STYLE,
  background: "var(--brand-primary)",
  color: "var(--surface-card)",
  cursor: "default",
  boxShadow: "0 1px 4px rgba(0,0,0,0.18)",
};

const BTN_INACTIVE_STYLE: CSSProperties = {
  ...BTN_BASE_STYLE,
  background: "transparent",
  color: "var(--surface-muted-foreground)",
  cursor: "pointer",
};
