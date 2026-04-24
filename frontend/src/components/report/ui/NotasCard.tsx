"use client";

import { useEffect, useRef, useState } from "react";

export type NotasSaveState = "idle" | "saving" | "saved" | "error";

/** ADR-117/123 · Fase 3 — NotasCard (T6) UI.
 *
 * Controlled textarea com autosave via callback. Backend persistence
 * (endpoint /v1/reports/{id}/notes) wire-up na Fase 8. Aqui apenas a
 * UI + debounce local. Indicador `saveState` reflete status externo.
 */
export interface NotasCardProps {
  readonly value: string;
  readonly onChange: (next: string) => void;
  readonly saveState?: NotasSaveState;
  readonly debounceMs?: number;
  readonly maxChars?: number;
  readonly onCopyMarkdown?: () => void;
  readonly onClear?: () => void;
  readonly className?: string;
}

export function NotasCard({
  value,
  onChange,
  saveState = "idle",
  debounceMs = 500,
  maxChars = 5000,
  onCopyMarkdown,
  onClear,
  className,
}: NotasCardProps) {
  const [draft, setDraft] = useState(value);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    setDraft(value);
  }, [value]);

  useEffect(() => {
    if (draft === value) return;
    if (timerRef.current) window.clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(() => {
      onChange(draft);
    }, debounceMs);
    return () => {
      if (timerRef.current) window.clearTimeout(timerRef.current);
    };
  }, [draft, value, onChange, debounceMs]);

  return (
    <section
      className={className}
      style={{
        background: "var(--surface-card)",
        borderRadius: "var(--radius-card, 12px)",
        overflow: "hidden",
        border: "1px solid var(--surface-border)",
        boxShadow: "var(--shadow-card)",
      }}
      data-notas-card
    >
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "var(--space-lg, 16px) var(--space-xl, 20px)",
          borderBottom: "1px solid var(--surface-border)",
        }}
      >
        <h3
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "var(--report-font-size-md, 14px)",
            fontWeight: 700,
            margin: 0,
            color: "var(--brand-primary)",
          }}
        >
          Notas e observações
        </h3>
        <SaveIndicator state={saveState} />
      </header>
      <textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value.slice(0, maxChars))}
        aria-label="Notas do relatório"
        placeholder="Anotações pessoais sobre este período…"
        style={{
          width: "100%",
          border: 0,
          borderRadius: 0,
          minHeight: 140,
          padding: "var(--space-lg, 16px) var(--space-xl, 20px)",
          fontSize: "var(--report-font-size-base, 13px)",
          lineHeight: 1.7,
          resize: "vertical",
          background: "transparent",
          color: "inherit",
          outline: "none",
          fontFamily: "inherit",
        }}
      />
      <footer
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "var(--space-md, 12px) var(--space-xl, 20px)",
          borderTop: "1px solid var(--surface-border)",
          background: "var(--report-surface-row-total, var(--surface-muted))",
        }}
      >
        <span
          style={{
            fontSize: "var(--report-font-size-xs, 10px)",
            color: "var(--surface-muted-foreground)",
          }}
        >
          {draft.length} / {maxChars}
        </span>
        <div style={{ display: "flex", gap: 8 }}>
          {onCopyMarkdown && (
            <NotasActionBtn onClick={onCopyMarkdown}>Copiar markdown</NotasActionBtn>
          )}
          {onClear && draft.length > 0 && (
            <NotasActionBtn onClick={onClear} danger>
              Limpar
            </NotasActionBtn>
          )}
        </div>
      </footer>
    </section>
  );
}

function SaveIndicator({ state }: { state: NotasSaveState }) {
  const label =
    state === "saving"
      ? "salvando…"
      : state === "saved"
        ? "salvo"
        : state === "error"
          ? "erro"
          : "";
  const dotColor =
    state === "saving"
      ? "var(--brand-warning)"
      : state === "error"
        ? "var(--brand-danger)"
        : "var(--brand-accent)";
  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 6,
        fontSize: "var(--report-font-size-xs, 10px)",
        color: "var(--surface-muted-foreground)",
      }}
    >
      <span
        aria-hidden="true"
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: dotColor,
        }}
      />
      {label}
    </div>
  );
}

function NotasActionBtn({
  children,
  onClick,
  danger = false,
}: {
  children: string;
  onClick: () => void;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        fontSize: "var(--report-font-size-xs, 10px)",
        padding: "6px 12px",
        borderRadius: "var(--radius-md, 6px)",
        border: "1px solid var(--surface-border)",
        background: "var(--surface-card)",
        cursor: "pointer",
        color: danger ? "var(--brand-danger)" : "var(--surface-muted-foreground)",
        fontWeight: 500,
      }}
    >
      {children}
    </button>
  );
}
