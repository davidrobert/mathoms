"use client";

import { useReportMode } from "@/components/report/ReportModeProvider";
import type { ReportMode } from "@/generated/report-layout";

const LABEL: Record<ReportMode, string> = {
  estrategico: "Estratégico",
};

/** ADR-117 · Fase 4 — toggle de modo integrado com ReportModeProvider.
 *
 * ADR-151 (Direção E): Modo Tático removido. ADR-168 (A8.4 PR4): Modo USA
 * removido. Modo Estratégico é único — toggle permanece como ponto de
 * extensão para futuro modo internacional generalizado.
 */
export function ModeToggle({
  className,
  compact = false,
}: {
  readonly className?: string;
  readonly compact?: boolean;
}) {
  const { mode, setMode } = useReportMode();
  const modes: readonly ReportMode[] = ["estrategico"];

  return (
    <div
      role="group"
      aria-label="Modo do relatório"
      className={className}
      style={{
        display: "inline-flex",
        gap: 2,
        padding: "6px 0",
        flexShrink: 0,
      }}
    >
      {modes.map((m) => {
        const active = m === mode;
        return (
          <button
            key={m}
            type="button"
            onClick={() => setMode(m)}
            aria-pressed={active}
            data-mode={m}
            data-active={active}
            style={{
              fontFamily: "var(--font-body)",
              fontSize: 11,
              fontWeight: 600,
              padding: compact ? "4px 8px" : "5px 12px",
              border: `1px solid ${active ? "rgba(255,255,255,0.25)" : "rgba(255,255,255,0.15)"}`,
              borderRadius: "var(--radius-md, 6px)",
              background: active ? "rgba(255,255,255,0.12)" : "transparent",
              color: active ? "#fff" : "rgba(255,255,255,0.5)",
              cursor: "pointer",
              transition: "all 0.2s",
              whiteSpace: "nowrap",
            }}
          >
            {LABEL[m]}
          </button>
        );
      })}
    </div>
  );
}
