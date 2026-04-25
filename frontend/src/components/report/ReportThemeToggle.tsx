"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";

/** ADR-117 — theme toggle do relatório premium.
 *
 * Wrappa `next-themes` (já configurado em layout.tsx com attribute="class").
 * Renderiza um controle segmentado Light|Dark matching EXEMPLO_DE_RELATORIO.html
 * §theme-toggle (linhas 562-568). Integração na top-nav fica para Fase 4.
 */
type ThemeValue = "light" | "dark";

export function ReportThemeToggle({
  className,
}: {
  className?: string;
}) {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const current: ThemeValue =
    mounted && resolvedTheme === "dark" ? "dark" : "light";

  return (
    <div
      className={className}
      role="group"
      aria-label="Tema do relatório"
      data-report-theme-toggle
      style={{ display: "inline-flex", gap: 2 }}
    >
      {(["light", "dark"] satisfies ThemeValue[]).map((value) => {
        const active = current === value;
        return (
          <button
            key={value}
            type="button"
            onClick={() => setTheme(value)}
            aria-pressed={active}
            data-active={active}
            data-theme-value={value}
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
            {value === "light" ? "Light" : "Dark"}
          </button>
        );
      })}
    </div>
  );
}
