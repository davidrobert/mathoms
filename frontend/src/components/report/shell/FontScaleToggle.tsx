"use client";

import {
  useReportFontScale,
  type ReportFontScale,
} from "@/components/report/useReportFontScale";

const LABEL: Record<ReportFontScale, string> = {
  compact: "Compacto",
  normal: "Normal",
  comfortable: "Confortável",
};

/** ADR-121 · Fase 4 — toggle de escala de fonte (13/15/17px).
 *
 * Segmented control matching `.theme-toggle` style, usa
 * useReportFontScale hook da Fase 1 para persistir em localStorage.
 * O escopo CSS `[data-font-scale="..."]` é aplicado pelo ReportShell
 * (caller lê `scale` e propaga no wrapper do shell).
 */
export function FontScaleToggle({ className }: { className?: string }) {
  const { scale, setScale } = useReportFontScale();
  const scales: readonly ReportFontScale[] = [
    "compact",
    "normal",
    "comfortable",
  ];
  return (
    <div
      role="group"
      aria-label="Tamanho da fonte"
      className={className}
      style={{ display: "inline-flex", gap: 2 }}
    >
      {scales.map((s) => {
        const active = s === scale;
        return (
          <button
            key={s}
            type="button"
            onClick={() => setScale(s)}
            aria-pressed={active}
            data-font-scale-value={s}
            data-active={active}
            style={{
              fontFamily: "var(--font-body)",
              fontSize: 11,
              fontWeight: 600,
              padding: "5px 12px",
              border: `1px solid ${active ? "rgba(255,255,255,0.25)" : "rgba(255,255,255,0.15)"}`,
              borderRadius: "var(--radius-md, 6px)",
              background: active ? "rgba(255,255,255,0.12)" : "transparent",
              color: active ? "#fff" : "rgba(255,255,255,0.5)",
              cursor: "pointer",
              transition: "all 0.2s",
            }}
          >
            {LABEL[s]}
          </button>
        );
      })}
    </div>
  );
}
