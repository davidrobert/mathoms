"use client";

/** ADR-117 · Fase 2 — navegação temporal para charts paginados.
 *
 * Matching `.chart-nav` do EXEMPLO_DE_RELATORIO.html (linhas 349-379):
 * 2 botões redondos (‹ ›) + label central + dots abaixo.
 */
export interface ChartNavProps {
  readonly label: string;
  readonly page: number;
  readonly total: number;
  readonly onPrev: () => void;
  readonly onNext: () => void;
  readonly className?: string;
}

export function ChartNav({
  label,
  page,
  total,
  onPrev,
  onNext,
  className,
}: ChartNavProps) {
  return (
    <div className={className} data-chart-nav>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 12,
          marginBottom: 10,
          userSelect: "none",
        }}
      >
        <button
          type="button"
          onClick={onPrev}
          disabled={page <= 0}
          aria-label="Período anterior"
          style={chartNavBtnStyle}
        >
          ‹
        </button>
        <span
          style={{
            fontSize: "var(--report-font-size-sm, 12px)",
            fontWeight: 600,
            color: "var(--surface-foreground)",
            minWidth: 140,
            textAlign: "center",
          }}
        >
          {label}
        </span>
        <button
          type="button"
          onClick={onNext}
          disabled={page >= total - 1}
          aria-label="Próximo período"
          style={chartNavBtnStyle}
        >
          ›
        </button>
      </div>
      <div
        style={{
          display: "flex",
          gap: 5,
          justifyContent: "center",
          marginTop: 8,
        }}
        aria-hidden="true"
      >
        {Array.from({ length: total }, (_, i) => (
          <span
            key={i}
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: i === page ? "var(--brand-accent)" : "var(--surface-border)",
              transition: "background 0.2s",
            }}
          />
        ))}
      </div>
    </div>
  );
}

const chartNavBtnStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  width: 32,
  height: 32,
  borderRadius: "50%",
  border: "1.5px solid var(--surface-border)",
  background: "var(--surface-background)",
  color: "var(--surface-foreground)",
  cursor: "pointer",
  fontSize: 16,
  fontWeight: 700,
  transition: "background 0.15s, opacity 0.15s",
};
